# CR AutoSpady PDF

Program dodaje 3 mm spadu z kazdej strony przez rozciaganie fragmentow krawedzi.
Obsluguje PDF jedno- i wielostronicowe oraz pliki JPG/JPEG. Wynik mozna zapisac
jako PDF albo JPG.

Domyslna zasada jest taka jak w starym programie: pasek 2 mm jest rozciagany do 5 mm.

## Gotowa wersja na inne komputery

Gotowy program jest tutaj:

```text
dist\CR AutoSpady PDF\CR AutoSpady PDF.exe
```

Do przeniesienia na inny komputer skopiuj caly folder `dist\CR AutoSpady PDF`
albo uzyj gotowego archiwum:

```text
CR_AutoSpady_PDF_portable.zip
```

Po rozpakowaniu uruchom `CR AutoSpady PDF.exe`.

## Praca w programie

1. Przeciagnij pliki do okna albo kliknij `Wybierz pliki`.
2. Kliknij `Dodaj spady`.
3. Sprawdz podglad.
4. Kliknij `Zapisz`, wybierz folder oraz format `PDF` albo `JPG`.

Po zapisie program automatycznie otwiera folder z gotowymi plikami.

## CR Rozklad SRA3

W repozytorium jest osobny program do rozmieszczania przez powielenie drukow
na arkuszu SRA3:

```powershell
python imposition_app.py
```

Mozna tez uzyc pliku `Uruchom Rozklad SRA3.bat`.

Program obsluguje:

- arkusz SRA3 450 x 320 oraz 320 x 450,
- odstep 3 mm miedzy uzytkami albo rozklad bez odstepu,
- tryb 1 str. i 2 str.,
- podpis na gorze arkusza, np. nazwe zamowienia,
- presety wizytowek, voucherow, ulotek A7/A6/DL/A5 i formatu 100 x 100.

Tryb `2 str.` bierze kolejne pary stron PDF jako awers i rewers, a rewers uklada
w lustrzanej kolejnosci kolumn, zeby pasowal do druku dwustronnego.

Build wersji EXE:

```powershell
.\Buduj Rozklad SRA3 EXE.bat
```

## Uruchomienie z kodu

```powershell
pip install -r requirements.txt
python desktop_app.py
```

Mozna tez uzyc pliku `Uruchom AutoSpady PDF.bat`.

## CR Kalkulator PDF

W repozytorium jest tez osobny program do wyceny i raportowania PDF:

```powershell
python quote_app.py
```

Mozna tez uzyc pliku `Uruchom Kalkulator PDF.bat`.

Program obsluguje jeden lub wiele plikow PDF i pokazuje:

- liczbe stron A4, A3, A2, A1, A0,
- inne rozmiary stron z sumowaniem takich samych wymiarow,
- liczbe stron kolorowych i czarno-bialych,
- sume m2 dla stron wiekszych od A3,
- wycene na podstawie zapisanego cennika,
- uslugi dodatkowe: skladanie do A4, dziurkowanie, wpinanie do skoroszytu,
  skany oraz jedna pozycje wlasna.

Przycisk `Zapisz PDF-y wg rozmiaru` tworzy oddzielny PDF dla kazdej grupy
rozmiaru stron. Cennik zapisuje sie w profilu uzytkownika Windows:
`%APPDATA%\CR PDF Kalkulator\pricing.json`.

Build wersji EXE:

```powershell
.\Buduj Kalkulator PDF.bat
```

## CR Winietki

Program tworzy PDF z winietkami na podstawie wbudowanych szablonow z katalogu.
Na starcie pokazuje miniaturki pogrupowane na Standard, Ozdobne, Dekoracyjne i
Zlote. Po wyborze szablonu wkleja sie liste osob, po jednej osobie w wierszu.
Kazda osoba trafia na osobna strone z tym samym wzorem.

```powershell
python winietki_app.py
```

Mozna tez uzyc pliku `Uruchom Winietki.bat`.

Program:

- wykrywa pozycje, rozmiar i kolor przykladowego nazwiska z szablonu,
- ma fonty zapisane na stale przy szablonach,
- usuwa przykladowe nazwisko bez zakrywania tla,
- dzieli za dlugie imiona i nazwiska na dwa wysrodkowane wiersze,
- dla O-05 przesuwa ozdobna linie pod tekst albo pomiedzy dwa wiersze,
- pokazuje podglad wszystkich stron przed zapisem,
- liczy koszt: cena szablonu x liczba osob.

Build wersji EXE:

```powershell
.\Buduj Winietki EXE.bat
```

## Budowanie EXE

```powershell
.\Buduj EXE.bat
```

## Tryb z linii polecen

```powershell
python -m cr_bleed wejscie.pdf
python -m cr_bleed wejscie.jpg
python -m cr_bleed wejscie.pdf wyjscie.pdf --engine vector
```

Tryb `vector` zachowuje PDF jako PDF i rozciaga krawedzie bez rasteryzowania calej strony.
Pliki JPG sa przetwarzane jako obraz i zapisywane do PDF ze spadami, a w aplikacji desktopowej mozna wybrac takze eksport JPG.
