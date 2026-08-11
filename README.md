# Link Check

Alliance Auth-plugin die in één tabel laat zien of je leden **goed met het
systeem gekoppeld** zijn.

CharLink weet welke apps een ESI-token nodig hebben en of een character daar in
zit, maar toont dat alleen per account of als kale ledenlijst per corp. Link
Check maakt daar een kruistabel van: **rij = AA-account, kolom = koppeling**.

## Wat je ziet

* Per account per koppeling: ✓ alles gekoppeld · `2/3` deels · ✕ niets · – niet
  van toepassing (het account heeft geen rechten voor die app).
* **Ingetrokken tokens**: er ligt nog een tokenrij, maar zonder `refresh_token`.
  Dat gebeurt als iemand z'n toestemming op de EVE-site intrekt — de app denkt
  dan dat het character gekoppeld is terwijl er niets meer op te halen valt.
* Filters op *niet compleet*, *ingetrokken tokens* en per corporatie.
* De AA-**state** in een eigen kolom: *Guest* oranje, *Member* groen, een eigen
  state (Blue, Corporation, …) neutraal — die zou een kleur geven die niets
  betekent.
* Sorteren door op een kolomkop te klikken: **Lid**, **corp**, **State**,
  **Chars** of **Status**; nog een klik draait de richting om. De sortering
  blijft staan als je daarna filtert of ververst.
* Zijn er koppelingen aangevinkt als verplicht, dan staan **alleen die** in de
  tabel — anders wordt hij onnodig breed.
* Detailpagina per account: welke van z'n characters welke koppeling mist, met
  een link naar CharLink om het in één keer recht te zetten.

De tabel wordt 10 minuten gecached; de knop **Ververs** rekent 'm opnieuw uit.

## Installatie

```bash
pip install git+https://github.com/jweijdert-eng/aa-linkcheck.git
```

Daarna in `local.py`:

```python
INSTALLED_APPS += ['linkcheck']
```

en:

```bash
python manage.py migrate linkcheck
python manage.py collectstatic
```

Herstart webserver **en** worker in dezelfde beweging als het installeren —
een menu-item dat naar een nog niet geladen app verwijst legt het hele
dashboard plat.

## Permissies

| Permissie             | Betekenis                                        |
|-----------------------|--------------------------------------------------|
| `linkcheck.basic_access` | Mag de eigen koppelstatus bekijken            |
| `linkcheck.auditor`      | Mag het overzicht van alle leden bekijken     |
| `linkcheck.manage_settings` | Mag de instellingen beheren (admin)        |

## Instellingen (admin → Link Check → instellingen)

* **Verplichte koppelingen** — een **aankruislijst** van alles wat CharLink
  kent; vink aan wat meetelt voor "compleet". Niets aangevinkt = alles waar het
  account recht op heeft. Achter elke naam staat het id, want twee apps mogen
  dezelfde weergavenaam hebben. Een aangevinkte koppeling waarvan de app
  verdwijnt blijft staan met de melding *niet meer geïnstalleerd*, zodat een
  eis nooit stilletjes wegvalt.
* **Alleen deze states** — welke AA-states op het overzicht horen. Leeg = elk
  account met een main, behalve Guest.
* **Guests meetellen** — zet Guests er alsnog bij.

## Vereist

`allianceauth>=5`, `django-esi>=8` en **aa-charlink** (de bron van de
koppelingen).
