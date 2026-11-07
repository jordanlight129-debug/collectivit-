"""Génération des exports Excel et PDF à partir des tableaux métier existants."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence
from xml.sax.saxutils import escape

import sqlite3
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from app.models.exercice import Exercice
from app.repositories import amendes, cotisations_paralleles, depenses, exercices, membres
from app.security import audit
from app.services import (
    amende_service, bilan_service, tableau_funeraire, tableau_mensuel, tableau_parallele,
)
from app.services.regles import month_label

REPORT_TITLES = {
    "balance": "Bilan de l’exercice",
    "funeral": "Cotisations funéraires",
    "members": "Liste des membres",
    "debts": "Dettes à recouvrer",
    "monthly": "Cotisations mensuelles",
    "expenses": "Journal des dépenses",
    "audit": "Journal d’audit",
}


@dataclass(frozen=True)
class ReportTable:
    title: str
    exercise_label: str
    headers: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]


def _totaux_membres(conn: sqlite3.Connection, exercise_id: int) -> dict[int, list[int]]:
    result = {member.id: [0, 0, 0, 0] for member in membres.list_(conn)}

    def add(member_id: int, due: int, paid: int, debt: int, advance: int = 0) -> None:
        totals = result.setdefault(member_id, [0, 0, 0, 0])
        for index, value in enumerate((due, paid, debt, advance)):
            totals[index] += value

    monthly = tableau_mensuel.tableau(conn, exercise_id)
    for line in monthly.lignes:
        statement = line.releve
        add(line.membre.id, statement.total_due, statement.total_paid,
            statement.total_debt, statement.advance)

    funeral = tableau_funeraire.tableau(conn, exercise_id)
    for line in funeral.lignes:
        statement = line.releve
        add(line.membre.id, statement.total_due, statement.cash_total,
            statement.total_debt, statement.advance)

    for subscription in cotisations_paralleles.list_for_exercice(conn, exercise_id):
        page = tableau_parallele.tableau(conn, subscription.id)
        for line in page.lignes:
            statement = line.releve
            add(line.membre.id, statement.due, statement.paid, statement.debt,
                statement.advance)

    for line in amende_service.lister(conn, exercise_id).lignes:
        fine = line.amende
        add(fine.membre_id, fine.montant_attendu, fine.montant_collecte,
            fine.manque_a_gagner)
    return result


def _bilan(conn: sqlite3.Connection, exercise: Exercice, label: str) -> ReportTable:
    bilan = bilan_service.calculer(conn, exercise.id)
    headers = ("Rubrique", "Dû", "Perçu", "Dettes restantes", "Avances", "Manque à gagner")
    rows = [
        (line.libelle, line.du if line.du is not None else "", line.percu,
         line.dettes, line.avances, line.manque if line.manque is not None else "")
        for line in bilan.lignes
    ]
    rows.extend((
        ("Total des entrées", "", bilan.total_entrees, "", "", ""),
        ("Dépenses", "", bilan.depenses, "", "", ""),
        ("Solde de l’exercice", "", bilan.solde, "", "", ""),
        ("Solde d’ouverture", "", bilan.solde_ouverture, "", "", ""),
        ("Solde cumulé", "", bilan.solde_cumule, "", "", ""),
    ))
    return ReportTable(REPORT_TITLES["balance"], label, headers, tuple(rows))


def _cotisations_funeraire(conn: sqlite3.Connection, exercise: Exercice, label: str) -> ReportTable:
    page = tableau_funeraire.tableau(conn, exercise.id)
    deaths = page.collectes
    headers = (
        "N° carnet", "Membre",
        *(f"{death.date_deces:%d/%m/%Y} · {death.nom_defunt or 'Membre'}" for death in deaths),
        "Dû total", "Perçu", "Dette restante", "Avance",
    )
    rows = []
    for line in page.lignes:
        cells = tuple("—" if cell.reason else f"{cell.paid} / {cell.due}"
                      for cell in line.releve.cells)
        rows.append((line.membre.numero_carnet, line.membre.nom, *cells,
                     line.releve.total_due, line.releve.cash_total,
                     line.releve.total_debt, line.releve.advance))
    return ReportTable(REPORT_TITLES["funeral"], label, headers, tuple(rows))


def _membres(conn: sqlite3.Connection, exercise: Exercice, label: str) -> ReportTable:
    totals = _totaux_membres(conn, exercise.id)
    headers = ("N° carnet", "Nom complet", "Sexe", "Adhésion", "Statut",
               "Dû (FCFA)", "Perçu (FCFA)", "Dette (FCFA)", "Avance (FCFA)")
    rows = []
    for member in membres.list_(conn):
        due, paid, debt, advance = totals.get(member.id, [0, 0, 0, 0])
        rows.append((member.numero_carnet, member.nom, member.sexe.value,
                     member.date_adhesion.strftime("%d/%m/%Y"), member.statut,
                     due, paid, debt, advance))
    return ReportTable(REPORT_TITLES["members"], label, headers, tuple(rows))


def _dettes(conn: sqlite3.Connection, exercise: Exercice, label: str) -> ReportTable:
    rows: list[tuple[object, ...]] = []
    for line in tableau_mensuel.tableau(conn, exercise.id).lignes:
        if line.releve.total_debt:
            rows.append((line.membre.numero_carnet, line.membre.nom,
                         "Cotisations mensuelles", "Exercice et reports",
                         line.releve.total_debt))

    for line in tableau_funeraire.tableau(conn, exercise.id).lignes:
        if line.releve.total_debt:
            rows.append((line.membre.numero_carnet, line.membre.nom,
                         "Cotisations funéraires", "Collectes de l’exercice et reports",
                         line.releve.total_debt))

    for subscription in cotisations_paralleles.list_for_exercice(conn, exercise.id):
        page = tableau_parallele.tableau(conn, subscription.id)
        for line in page.lignes:
            if line.releve.debt:
                rows.append((line.membre.numero_carnet, line.membre.nom,
                             "Cotisations parallèles", subscription.nom, line.releve.debt))

    for line in amendes.list_(conn, exercise.id):
        if line.amende.manque_a_gagner:
            rows.append((line.numero_carnet, line.membre_nom, "Amendes",
                         line.amende.libelle, line.amende.manque_a_gagner))

    rows.sort(key=lambda row: (str(row[1]).casefold(), str(row[2]), str(row[3])))
    headers = ("N° carnet", "Membre", "Rubrique", "Détail", "Montant restant (FCFA)")
    return ReportTable(REPORT_TITLES["debts"], label, headers, tuple(rows))


def _mensuel(conn: sqlite3.Connection, exercise: Exercice, label: str) -> ReportTable:
    page = tableau_mensuel.tableau(conn, exercise.id)
    month_names = ("SEP", "OCT", "NOV", "DÉC", "JAN", "FÉV", "MAR", "AVR",
                   "MAI", "JUIN", "JUIL", "AOÛT")
    headers = ("N° carnet", "Membre", *month_names, "Dû", "Perçu", "Dette", "Avance")
    rows = []
    for line in page.lignes:
        paid = tuple(cell.paid if cell.due else "" for cell in line.releve.cells)
        rows.append((line.membre.numero_carnet, line.membre.nom, *paid,
                     line.releve.total_due, line.releve.total_paid,
                     line.releve.total_debt, line.releve.advance))
    return ReportTable(REPORT_TITLES["monthly"], label, headers, tuple(rows))


def _depenses(conn: sqlite3.Connection, exercise: Exercice, label: str) -> ReportTable:
    headers = ("Date", "Libellé", "Bénéficiaire", "Montant prévu (FCFA)",
               "Montant dépensé (FCFA)", "Reliquat", "Montant du reliquat (FCFA)")
    rows = []
    for line in depenses.list_(conn, exercise.id):
        expense = line.depense
        rows.append((expense.date_depense.strftime("%d/%m/%Y"), expense.libelle,
                     expense.beneficiaire or "—", expense.montant_prevu,
                     expense.montant_depense,
                     line.reliquat.nom if line.reliquat else "—",
                     line.reliquat.montant if line.reliquat else 0))
    return ReportTable(REPORT_TITLES["expenses"], label, headers, tuple(rows))


def _journal_audit(conn: sqlite3.Connection, exercise: Exercice, label: str) -> ReportTable:
    headers = ("Date et heure", "Utilisateur", "Rôle", "Action", "Objet", "Détail")
    rows = []
    total = audit.count_entries(conn)
    for offset in range(0, total, 500):
        entries = audit.list_entries(conn, limit=min(500, total - offset), offset=offset)
        rows.extend(
            (entry["date_heure"], entry["identifiant"], entry["role"], entry["action"],
             entry["objet"] or "—", entry["detail"] or "")
            for entry in entries
        )
    return ReportTable(REPORT_TITLES["audit"], label, headers, tuple(rows))


_BUILDERS = {
    "balance": _bilan,
    "funeral": _cotisations_funeraire,
    "members": _membres,
    "debts": _dettes,
    "monthly": _mensuel,
    "expenses": _depenses,
    "audit": _journal_audit,
}


def build_report(conn: sqlite3.Connection, exercise_label: str, report_key: str) -> ReportTable:
    exercise = exercices.get_by_libelle(conn, exercise_label)
    if exercise is None:
        raise ValueError(f"Exercice introuvable : {exercise_label}")
    try:
        builder = _BUILDERS[report_key]
    except KeyError:
        raise ValueError(f"Rapport inconnu : {report_key}") from None
    return builder(conn, exercise, exercise_label)


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return cleaned or "rapport"


def write_excel(path: Path, report: ReportTable) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = _safe_filename(report.title)[:31]
    sheet.append([report.title])
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(report.headers))
    sheet.append([f"Exercice {report.exercise_label}"])
    sheet.append([])
    sheet.append(list(report.headers))

    for row in report.rows:
        sheet.append(list(row))

    title_font = Font(name="Calibri", size=16, bold=True, color="0B1F3F")
    sheet.cell(1, 1).font = title_font
    sheet.cell(2, 1).font = Font(italic=True, color="6B7280")
    for cell in sheet[4]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0B1F3F")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for row in sheet.iter_rows(min_row=5):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if isinstance(cell.value, (int, float)):
                cell.number_format = "#,##0"

    sheet.freeze_panes = "A5"
    sheet.auto_filter.ref = f"A4:{get_column_letter(len(report.headers))}{max(sheet.max_row, 4)}"
    for column in range(1, len(report.headers) + 1):
        values = [str(sheet.cell(row, column).value or "") for row in range(4, sheet.max_row + 1)]
        sheet.column_dimensions[get_column_letter(column)].width = min(max(map(len, values), default=10) + 2, 40)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return path


def write_pdf(path: Path, report: ReportTable) -> Path:
    page_size = landscape(A4) if len(report.headers) > 7 else A4
    document = SimpleDocTemplate(str(path), pagesize=page_size,
                                 leftMargin=28, rightMargin=28, topMargin=30, bottomMargin=30,
                                 title=report.title, author="Solidarité Étoile")
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.textColor = colors.HexColor("#0B1F3F")
    subtitle_style = ParagraphStyle("ReportSubtitle", parent=styles["Normal"],
                                    textColor=colors.HexColor("#6B7280"), spaceAfter=12)
    cell_style = ParagraphStyle("ReportCell", parent=styles["Normal"], fontName="Helvetica",
                                fontSize=7, leading=9, wordWrap="CJK")
    header_style = ParagraphStyle("ReportHeader", parent=cell_style, textColor=colors.white,
                                  fontName="Helvetica-Bold", alignment=TA_CENTER)
    story = [Paragraph(escape(report.title), title_style),
             Paragraph(f"Exercice {escape(report.exercise_label)}", subtitle_style), Spacer(1, 6)]
    data = [[Paragraph(escape(header), header_style) for header in report.headers]]
    data.extend([
        [Paragraph(escape(str(value)).replace("\n", "<br/>"), cell_style) for value in row]
        for row in report.rows
    ])
    widths = [document.width / len(report.headers)] * len(report.headers)
    table = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3F")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         (colors.white, colors.HexColor("#F0F1F4"))),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E4EA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.build(story)
    return path


def export_report(conn: sqlite3.Connection, exercise_label: str, report_key: str,
                  file_format: str, output_dir: Path | None = None) -> Path:
    if file_format not in ("excel", "pdf"):
        raise ValueError(f"Format d’export non pris en charge : {file_format}")
    report = build_report(conn, exercise_label, report_key)
    from app.config import ASSOCIATION_NAME, EXPORT_DIR

    directory = output_dir or EXPORT_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = "xlsx" if file_format == "excel" else "pdf"
    filename = f"{_safe_filename(report.title)}_{_safe_filename(exercise_label)}_{timestamp}.{suffix}"
    target = directory / filename
    return write_excel(target, report) if file_format == "excel" else write_pdf(target, report)