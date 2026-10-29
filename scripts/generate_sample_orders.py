"""Generate synthetic vehicle-order PDFs for testing the contract checker.

The documents mirror the structure of a real German vehicle purchase order
(Bestellung, equipment list, price summary, terms, signature sheet, payment
schedule) but every person, company, address, number and clause is fictional.

Usage:
    uv run scripts/generate_sample_orders.py [output_dir]
"""

from __future__ import annotations

import logging
import sys
import textwrap
import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pymupdf

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "documents" / "samples"

PAGE_WIDTH, PAGE_HEIGHT = pymupdf.paper_size("a4")
LEFT, RIGHT = 56.0, PAGE_WIDTH - 56.0
TOP, BOTTOM = 70.0, PAGE_HEIGHT - 95.0
FONT, FONT_BOLD = "helv", "hebo"
WRAP_CHARS = 100

VAT_RATE = Decimal("0.19")
CENT = Decimal("0.01")
BRAND = "Musterauto"
ISSUER_LINES = (
    "Musterauto AG | Beispielstraße 1 | 12345 Musterstadt | www.example.com | USt.-Id. Nr. DE000000000",
    "Beispielbank AG | IBAN: DE00 0000 0000 0000 0000 00 | BIC: XXXXDEXXXXX | Registergericht Musterstadt HRB 00000",
)


@dataclass(frozen=True)
class Address:
    name: str
    street: str
    city: str


@dataclass(frozen=True)
class Advisor:
    name: str
    phone: str
    mobile: str
    email: str


@dataclass(frozen=True)
class Item:
    code: str
    label: str
    price: Decimal = Decimal("0")


@dataclass(frozen=True)
class SampleOrder:
    file_name: str
    buyer: Address
    reference: str
    dealer: Address
    advisor: Advisor
    order_date: str
    vehicle: str
    model_code: str
    drive: str
    base_price: Decimal
    paint: Item
    upholstery: Item
    items: tuple[Item, ...]
    discount_percent: Decimal
    transfer_cost: Decimal
    delivery: str
    framework_contract: str
    signer: str
    sign_place: str

    @property
    def deal_id(self) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"sample-order/{self.file_name}"))


@dataclass(frozen=True)
class Totals:
    list_sum: Decimal
    discount: Decimal
    vehicle_net: Decimal
    vehicle_vat: Decimal
    transfer_vat: Decimal
    purchase_net: Decimal
    purchase_vat: Decimal
    purchase_gross: Decimal

    @property
    def transfer_gross(self) -> Decimal:
        return self.purchase_gross - self.payment_after_handover

    @property
    def payment_after_handover(self) -> Decimal:
        return self.vehicle_net + self.vehicle_vat


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def compute_totals(order: SampleOrder) -> Totals:
    """Calculate the price summary the same way the original order does."""
    list_sum = order.base_price + sum((i.price for i in order.items), Decimal("0"))
    discount = _round(list_sum * order.discount_percent / 100)
    vehicle_net = list_sum - discount
    vehicle_vat = _round(vehicle_net * VAT_RATE)
    transfer_vat = _round(order.transfer_cost * VAT_RATE)
    return Totals(
        list_sum=list_sum,
        discount=discount,
        vehicle_net=vehicle_net,
        vehicle_vat=vehicle_vat,
        transfer_vat=transfer_vat,
        purchase_net=vehicle_net + order.transfer_cost,
        purchase_vat=vehicle_vat + transfer_vat,
        purchase_gross=vehicle_net + order.transfer_cost + vehicle_vat + transfer_vat,
    )


def format_eur(value: Decimal) -> str:
    """Format as German currency amount, e.g. 55.694,00; zero is shown as -,--."""
    if value == 0:
        return "-,--"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class PageWriter:
    """Writes text top-to-bottom, starting a new page when the current one is full."""

    def __init__(self, doc: pymupdf.Document) -> None:
        self._doc = doc
        self._page: pymupdf.Page | None = None
        self.y = BOTTOM

    def new_page(self) -> None:
        self._page = self._doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self.y = TOP

    def gap(self, height: float) -> None:
        self.y += height

    def text(self, text: str, x: float = LEFT, size: float = 10, bold: bool = False) -> None:
        self._ensure_space(size * 1.5)
        self._insert(x, text, size, bold)
        self.y += size * 1.5

    def row(self, columns: tuple[tuple[float, str], ...], amount: str, size: float = 9.5) -> None:
        self._ensure_space(size * 1.5)
        for x, value in columns:
            self._insert(x, value, size, False)
        self._insert_right(amount, size, False)
        self.y += size * 1.5

    def amount_line(self, label: str, amount: str, bold: bool = False) -> None:
        self._ensure_space(15)
        self._insert(LEFT, label, 10, bold)
        self._insert_right(amount, 10, bold)
        self.y += 15

    def paragraph(self, text: str, size: float = 9) -> None:
        for line in textwrap.wrap(text, WRAP_CHARS):
            self.text(line, size=size)
        self.gap(4)

    def rule(self) -> None:
        self._page.draw_line((LEFT, self.y), (RIGHT, self.y), width=0.5)
        self.gap(10)

    def _ensure_space(self, height: float) -> None:
        if self._page is None or self.y + height > BOTTOM:
            self.new_page()

    def _insert(self, x: float, text: str, size: float, bold: bool) -> None:
        self._page.insert_text((x, self.y), text, fontsize=size, fontname=FONT_BOLD if bold else FONT)

    def _insert_right(self, text: str, size: float, bold: bool) -> None:
        font = FONT_BOLD if bold else FONT
        width = pymupdf.get_text_length(text, fontname=font, fontsize=size)
        self._insert(RIGHT - width, text, size, bold)


def _write_letterhead(w: PageWriter, order: SampleOrder, title: str) -> None:
    w.new_page()
    w.text(BRAND, x=360, size=20)
    w.text(title, x=360, size=11, bold=True)
    w.gap(10)
    contact_y = w.y
    w.text("Käufer:", bold=True)
    for line in (order.buyer.name, order.buyer.street, order.buyer.city, "", f"Kundenreferenz 1: {order.reference}"):
        w.text(line)
    end_y = w.y
    w.y = contact_y
    dealer_lines = (
        "Sie werden betreut durch", order.dealer.name, order.dealer.street, order.dealer.city, "",
        "Ihr Ansprechpartner", order.advisor.name, f"Tel.: {order.advisor.phone}",
        f"Mobil: {order.advisor.mobile}", "", "Datum", order.order_date,
    )
    for line in dealer_lines:
        w.text(line, x=360, size=9.5)
    w.y = max(end_y, w.y) + 10


def _write_order(w: PageWriter, order: SampleOrder, totals: Totals) -> None:
    _write_letterhead(w, order, "Bestellung")
    w.paragraph(
        "Unter Einbeziehung der beiliegenden Neufahrzeug-Verkaufsbedingungen und der beiliegenden "
        "Laufzeitregelung für die Digitalen Extras bestellt der Käufer bei der Musterauto AG:"
    )
    w.text(order.vehicle, size=11, bold=True)
    w.row(((LEFT, "Baumuster:"), (160, order.model_code)), "")
    w.row(((LEFT, "Antriebsart:"), (160, order.drive)), "")
    w.gap(6)
    w.row(((LEFT, "Listenpreis (ohne Umsatzsteuer):"),), "EUR")
    w.row(((LEFT, "Fahrzeug in Grundausstattung ab Herstellerwerk"),), format_eur(order.base_price))
    w.row(((LEFT, "Lackierung:"), (160, order.paint.code), (200, order.paint.label)), format_eur(order.paint.price))
    w.row(((LEFT, "Polsterung:"), (160, order.upholstery.code), (200, order.upholstery.label)), format_eur(order.upholstery.price))
    w.gap(6)
    w.text("Ausstattungen", bold=True)
    for item in order.items:
        w.row(((LEFT, item.code), (120, item.label)), format_eur(item.price))
    _write_totals(w, order, totals)
    _write_order_details(w, order)


def _write_totals(w: PageWriter, order: SampleOrder, totals: Totals) -> None:
    w.gap(12)
    w.amount_line("Summe der Listenpreise", format_eur(totals.list_sum), bold=True)
    w.amount_line(f"Abzgl. Flottennachlass {order.discount_percent}%", f"-{format_eur(totals.discount)}")
    w.amount_line("Fahrzeugpreis (exkl. USt.)", format_eur(totals.vehicle_net), bold=True)
    w.amount_line("Zzgl. 19% gesetzl. Umsatzsteuer", format_eur(totals.vehicle_vat))
    w.amount_line("Überführungskosten (exkl. USt.)", format_eur(order.transfer_cost), bold=True)
    w.amount_line("Zzgl. 19% gesetzl. Umsatzsteuer", format_eur(totals.transfer_vat))
    w.amount_line("Kaufpreis (exkl. USt.)", format_eur(totals.purchase_net), bold=True)
    w.amount_line("Zzgl. 19% gesetzl. Umsatzsteuer", format_eur(totals.purchase_vat))
    w.rule()
    w.amount_line("Kaufpreis (inkl. USt.)", format_eur(totals.purchase_gross), bold=True)


def _write_order_details(w: PageWriter, order: SampleOrder) -> None:
    w.gap(14)
    w.paragraph(
        "Die oben genannten Preise sind die derzeitigen Listenpreise. Für die Kaufpreisvereinbarung "
        "und ein etwaiges Rücktrittsrecht gilt Abschnitt II. der Neufahrzeug-Verkaufsbedingungen."
    )
    details = (
        ("Zahlungsbedingung:", "Banküberweisung"),
        ("Vermittelt durch:", f"{order.dealer.name}, {order.dealer.street}, {order.dealer.city}"),
        ("Sie wurden beraten von:", f"{order.advisor.name}, {order.advisor.email}"),
        ("Bestelldatum:", order.order_date),
        ("Unverbindlicher Liefertermin:", order.delivery),
        ("Bereitstellungsort:", f"{order.dealer.name}, {order.dealer.city}"),
    )
    for label, value in details:
        w.row(((LEFT, label), (210, value)), "")
    w.gap(6)
    w.paragraph(
        f"Die Bestellung erfolgt auf Grundlage des Rahmenvertrags mit Vertragsnummer "
        f"{order.framework_contract}. Es bestehen Nachlass- oder Bonusvereinbarungen."
    )
    for heading, body in ORDER_NOTES:
        w.text(heading, size=9.5, bold=True)
        w.paragraph(body)


def _write_terms(w: PageWriter) -> None:
    w.new_page()
    w.text("Allgemeine Verkaufsbedingungen für Neufahrzeuge (Muster, Stand 01/2026)", size=12, bold=True)
    w.gap(6)
    for heading, body in TERMS:
        w.text(heading, size=9.5, bold=True)
        w.paragraph(body)


def _write_runtime_rules(w: PageWriter) -> None:
    w.new_page()
    w.text("Laufzeitregelungen für die Digitalen Extras", size=12, bold=True)
    w.gap(6)
    for paragraph in RUNTIME_RULES:
        w.paragraph(paragraph)


def _write_signature_sheet(w: PageWriter, order: SampleOrder) -> None:
    _write_letterhead(w, order, "Signaturblatt")
    w.text("Ihre Dokumente", bold=True)
    w.text("Mit meiner Unterschrift bestätige ich mein Einverständnis mit den angekreuzten Dokumenten:", size=9.5)
    w.gap(4)
    for document in ("Bestellung", "Neufahrzeug-Verkaufsbedingungen", "Laufzeitregelungen für die Digitalen Extras"):
        w.row(((LEFT, f"- {document}"),), "[X]")
    w.gap(6)
    w.text("sowie die Kenntnisnahme der angekreuzten Dokumente:", size=9.5)
    for document in ("Nutzungsbedingungen für Digitale Extras", "Musterauto ID Nutzungsbedingungen"):
        w.row(((LEFT, f"- {document}"),), "[X]")
    w.gap(40)
    w.row(((LEFT, f"{order.sign_place}, {order.order_date}"), (330, "gez. " + order.signer)), "")
    w.rule()
    w.row(((LEFT, "Ort, Datum"), (330, "Unterschrift des Käufers")), "")
    w.gap(8)
    w.row(((330, order.signer),), "")
    w.row(((330, "Name in Druckbuchstaben"),), "")


def _write_payment_schedule(w: PageWriter, order: SampleOrder, totals: Totals) -> None:
    _write_letterhead(w, order, "Zahlungsaufstellung")
    w.text("Ihre Zahlungsaufstellung", bold=True)
    w.row(((LEFT, ""),), "EUR")
    w.amount_line("Anzahlungsbetrag (inkl. USt.)", "0,00")
    w.amount_line("Kundenzahlung nach Übergabe (inkl. USt.)", format_eur(totals.payment_after_handover))
    w.amount_line("Überführungskosten (inkl. USt.)", format_eur(totals.transfer_gross))
    w.rule()
    w.amount_line("Kaufpreis (inkl. USt.)", format_eur(totals.purchase_gross), bold=True)


def _add_footers(doc: pymupdf.Document, order: SampleOrder) -> None:
    page_count = doc.page_count
    for number, page in enumerate(doc, start=1):
        y = PAGE_HEIGHT - 70
        page.insert_text((LEFT, y), f"Deal ID: {order.deal_id}", fontsize=7, fontname=FONT)
        page.insert_text((260, y), order.order_date, fontsize=7, fontname=FONT)
        page.insert_text((RIGHT - 45, y), f"Seite {number} / {page_count}", fontsize=7, fontname=FONT)
        page.draw_line((LEFT, y + 4), (RIGHT, y + 4), width=0.5)
        for offset, line in enumerate(ISSUER_LINES, start=1):
            page.insert_text((LEFT, y + 4 + offset * 10), line, fontsize=6.5, fontname=FONT)


def build_document(order: SampleOrder) -> pymupdf.Document:
    """Render the complete multi-page order for *order*."""
    totals = compute_totals(order)
    doc = pymupdf.open()
    writer = PageWriter(doc)
    _write_order(writer, order, totals)
    _write_signature_sheet(writer, order)
    _write_payment_schedule(writer, order, totals)
    _write_terms(writer)
    _write_runtime_rules(writer)
    _add_footers(doc, order)
    doc.set_metadata({"title": f"Bestellung {order.vehicle}", "author": "Sample generator", "subject": "Synthetic test data"})
    return doc


def generate(output_dir: Path) -> list[Path]:
    """Write every sample order to *output_dir* and return the created paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for order in SAMPLE_ORDERS:
        path = output_dir / order.file_name
        with build_document(order) as doc:
            doc.save(path, garbage=4, deflate=True)
        logger.info("Wrote %s", path)
        paths.append(path)
    return paths


ORDER_NOTES = (
    ("DIGITALE EXTRAS",
     "Digitale Extras sind teils kostenpflichtige digitale Zusatzfunktionen des Fahrzeugs. Ihre Nutzung setzt die "
     "Akzeptanz der jeweils gültigen Nutzungsbedingungen, die Verknüpfung des Fahrzeugs mit einem Benutzerkonto und "
     "gegebenenfalls die Aktivierung voraus. Die Laufzeiten ergeben sich aus der beiliegenden Laufzeitregelung."),
    ("LIEFERENGPÄSSE",
     "Ein verschuldensunabhängiges Beschaffungsrisiko wird nicht übernommen. Ist der Kaufgegenstand wegen "
     "Serienauslaufs nicht mehr lieferbar, werden beide Parteien von ihren Pflichten frei; dem Käufer wird ein "
     "vergleichbares Fahrzeug angeboten und geleistete Zahlungen werden unverzüglich erstattet."),
    ("DATENSCHUTZ",
     "Informationen zur Verarbeitung personenbezogener Daten finden Sie unter https://www.example.com/datenschutz."),
)

TERMS = (
    ("I. Vertragsabschluss",
     "Der Käufer ist an die Bestellung höchstens drei Wochen, bei Nutzfahrzeugen sechs Wochen gebunden. Der "
     "Kaufvertrag kommt zustande, wenn der Verkäufer die Annahme in Textform bestätigt oder die Lieferung ausführt. "
     "Die Übertragung von Rechten und Pflichten des Käufers bedarf der Zustimmung des Verkäufers."),
    ("II. Preise",
     "Der Preis versteht sich ab Herstellerwerk zuzüglich Überführungskosten und Umsatzsteuer. Bei Lieferung nach "
     "mehr als vier Monaten ändert sich der Kaufpreis im Verhältnis der Listenpreisänderung; übersteigt die Erhöhung "
     "drei Prozent, kann der Käufer binnen zwei Wochen in Textform zurücktreten."),
    ("III. Zahlung",
     "Kaufpreis und Nebenleistungen sind bei Übergabe und Aushändigung der Rechnung bargeldlos fällig. Aufrechnen "
     "kann der Käufer nur mit unbestrittenen oder rechtskräftig festgestellten Forderungen."),
    ("IV. Lieferung und Lieferverzug",
     "Liefertermine sind in Textform anzugeben. Sechs Wochen nach Überschreiten eines unverbindlichen Termins kann der "
     "Käufer zur Lieferung auffordern. Bei leichter Fahrlässigkeit ist der Verzugsschaden auf fünf Prozent des "
     "Kaufpreises begrenzt."),
    ("V. Abnahme",
     "Der Käufer nimmt das Fahrzeug innerhalb von 14 Tagen nach Bereitstellungsanzeige ab. Bei Nichtabnahme kann der "
     "Verkäufer pauschal 15 Prozent des Kaufpreises ohne Umsatzsteuer als Schadenersatz verlangen."),
    ("VI. Eigentumsvorbehalt",
     "Das Fahrzeug bleibt bis zum vollständigen Ausgleich aller Forderungen aus dem Kaufvertrag Eigentum des "
     "Verkäufers. Während dieser Zeit steht dem Verkäufer der Besitz der Zulassungsbescheinigung Teil II zu."),
    ("VII. Sachmängel",
     "Ansprüche wegen Sachmängeln verjähren in zwei Jahren ab Ablieferung, gegenüber Unternehmern in einem Jahr. "
     "Mängelansprüche können beim Verkäufer oder bei anerkannten Servicebetrieben geltend gemacht werden."),
    ("VIII. Haftung",
     "Für leicht fahrlässig verursachte Schäden haftet der Verkäufer nur bei Verletzung wesentlicher Vertragspflichten "
     "und begrenzt auf den vorhersehbaren typischen Schaden. Dies gilt nicht bei Verletzung von Leben, Körper oder "
     "Gesundheit."),
    ("IX. Gerichtsstand und anwendbares Recht",
     "Ist der Käufer Kaufmann, ist Gerichtsstand Musterstadt. Es gilt das Recht der Bundesrepublik Deutschland unter "
     "Ausschluss des UN-Kaufrechts."),
    ("X. Digitale Extras und Software-Updates",
     "Der Verkäufer stellt im Rahmen seiner vertraglichen und gesetzlichen Pflichten Software-Updates für Fahrzeug und "
     "Digitale Extras bereit. Digitale Extras mit begrenzter Laufzeit enden automatisch mit Ablauf der Laufzeit."),
)

RUNTIME_RULES = (
    "Die Laufzeit der Digitalen Extras beginnt mit der Fahrzeugübergabe oder mit der Aktivierung im Benutzerkonto, "
    "spätestens jedoch drei Monate nach der Erstzulassung.",
    "Unbegrenzte Laufzeit: Smartphone-Integration (D01), Festplatten-Navigation (D02).",
    "Laufzeit 3 Jahre ab Fahrzeugübergabe: Remote Services Plus (D10), Karten-Updates (D11).",
    "Laufzeit 7 Jahre ab Fahrzeugübergabe: Live-Verkehrsinformationen (D20), Updates Geschwindigkeitsassistent (D21).",
    "Endet die Laufzeit, kann der Käufer das Digitale Extra zu den dann geltenden Preisen verlängern, sofern es für "
    "das Fahrzeug noch angeboten wird. Andernfalls wird es am Ende der Laufzeit deaktiviert.",
)


def _eur(value: str) -> Decimal:
    return Decimal(value)


_DEALER = Address("Musterauto AG Niederlassung Musterstadt", "Autohausweg 12", "12345 Musterstadt")
_COMMON_ITEMS = (
    Item("B10", "Aktiver Brems-Assistent"),
    Item("B11", "HOLD-Funktion"),
    Item("B12", "Feststellbremse elektrisch", _eur("360.00")),
    Item("C20", "Aktiver Lenk-Assistent"),
    Item("C21", "Lenkradheizung", _eur("168.00")),
    Item("C22", "Multifunktionslenkrad"),
    Item("D01", "Digitales Extra: Smartphone-Integration"),
    Item("D10", "Digitales Extra: Remote Services Plus"),
    Item("E30", "Notrufsystem"),
    Item("E31", "Digitalradio (DAB)"),
    Item("E32", "USB-Steckdose 5 V"),
    Item("F40", "Cupholder vorn", _eur("26.00")),
    Item("F41", "Winter-Paket", _eur("608.00")),
    Item("F42", "Frontscheibe heizbar", _eur("399.00")),
    Item("H50", "Sitzheizung für Fahrer"),
    Item("H51", "Sitzheizung für Beifahrer"),
    Item("J60", "Totwinkel-Assistent"),
    Item("J61", "Verkehrszeichen-Assistent"),
    Item("J62", "Park-Paket mit 360°-Kamera", _eur("1233.00")),
    Item("L70", "LED-Scheinwerfer"),
    Item("S80", "Airbag Fahrer"),
    Item("S81", "Airbag Beifahrer"),
    Item("Y90", "Verbandstasche"),
    Item("Y91", "Warndreieck"),
)

SAMPLE_ORDERS = (
    SampleOrder(
        file_name="sample_order_transporter.pdf",
        buyer=Address("Musterfirma Facility GmbH", "Hauptstraße 1", "10115 Musterstadt"),
        reference="Objekt-ID 2026-0001, Max Mustermann",
        dealer=_DEALER,
        advisor=Advisor("Erika Beispiel", "+49 30 0000000-10", "+49 170 0000001", "erika.beispiel@example.com"),
        order_date="14.09.2026",
        vehicle="Musterauto Transporter Kastenwagen 315 D standard",
        model_code="M0000001",
        drive="RWD",
        base_price=_eur("55694.00"),
        paint=Item("P01", "arktikweiß"),
        upholstery=Item("U01", "Stoff schwarz"),
        items=_COMMON_ITEMS + (
            Item("G10", "Hochdach", _eur("2005.00")),
            Item("G11", "9-Gang-Automatikgetriebe", _eur("2642.00")),
            Item("G12", "Klimatisierungsautomatik", _eur("571.00")),
            Item("P30", "Assistenzsysteme-Paket", _eur("2213.00")),
            Item("P31", "Laderaum-Paket", _eur("1310.00")),
            Item("Q20", "Anhängerkupplung fest", _eur("528.00")),
        ),
        discount_percent=Decimal("32"),
        transfer_cost=_eur("750.00"),
        delivery="4. Quartal 2026",
        framework_contract="RV-0000-0001",
        signer="Max Mustermann",
        sign_place="Musterstadt",
    ),
    SampleOrder(
        file_name="sample_order_pickup.pdf",
        buyer=Address("Beispiel Logistik AG", "Industriering 7", "20095 Beispielhausen"),
        reference="Flotte Nord, Jonas Beispiel",
        dealer=_DEALER,
        advisor=Advisor("Paul Platzhalter", "+49 30 0000000-20", "+49 170 0000002", "paul.platzhalter@example.com"),
        order_date="02.10.2026",
        vehicle="Musterauto Pritsche Doppelkabine 319 D lang",
        model_code="M0000002",
        drive="AWD",
        base_price=_eur("61250.00"),
        paint=Item("P02", "graphitgrau metallic", _eur("890.00")),
        upholstery=Item("U02", "Kunstleder anthrazit", _eur("310.00")),
        items=_COMMON_ITEMS + (
            Item("G20", "Allradantrieb zuschaltbar", _eur("4120.00")),
            Item("G21", "Standheizung mit Fernbedienung", _eur("1450.00")),
            Item("P32", "Pritschen-Paket Aluminium", _eur("2380.00")),
        ),
        discount_percent=Decimal("25"),
        transfer_cost=_eur("890.00"),
        delivery="1. Quartal 2027",
        framework_contract="RV-0000-0002",
        signer="Jonas Beispiel",
        sign_place="Beispielhausen",
    ),
    SampleOrder(
        file_name="sample_order_minibus.pdf",
        buyer=Address("Testwerk Service GmbH", "Am Prüfstand 3", "50667 Testheim"),
        reference="Shuttle-Projekt, Lena Probe",
        dealer=_DEALER,
        advisor=Advisor("Erika Beispiel", "+49 30 0000000-10", "+49 170 0000001", "erika.beispiel@example.com"),
        order_date="21.10.2026",
        vehicle="Musterauto Kleinbus Tourer 317 D 9-Sitzer",
        model_code="M0000003",
        drive="FWD",
        base_price=_eur("58990.00"),
        paint=Item("P03", "obsidianschwarz metallic", _eur("990.00")),
        upholstery=Item("U03", "Stoff grau"),
        items=_COMMON_ITEMS + (
            Item("R10", "Fondsitzbank 3-sitzig, 2. Reihe", _eur("1180.00")),
            Item("R11", "Fondsitzbank 3-sitzig, 3. Reihe", _eur("1180.00")),
            Item("R12", "Klimaanlage im Fond", _eur("1890.00")),
            Item("R13", "Schiebetür links und rechts", _eur("760.00")),
        ),
        discount_percent=Decimal("18"),
        transfer_cost=_eur("650.00"),
        delivery="2. Quartal 2027",
        framework_contract="RV-0000-0003",
        signer="Lena Probe",
        sign_place="Testheim",
    ),
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT_DIR
    generate(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
