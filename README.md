# Patent Żeglarza

Lokalna aplikacja do nauki pytań egzaminacyjnych na patent żeglarza jachtowego.

## Jak uruchomić lokalnie

```bash
npm install
npm run dev
```

Potem otwórz adres pokazany w terminalu, zwykle:

```text
http://127.0.0.1:5173/
```

Nie uruchamiaj źródłowego `index.html` przez podwójne kliknięcie. To aplikacja React/Vite, więc potrzebuje lokalnego serwera developerskiego.

## Wersja produkcyjna lokalnie

```bash
npm run build
npm run preview
```

Potem otwórz:

```text
http://127.0.0.1:4173/
```

## Co jest w aplikacji

- 301 pytań z odpowiedziami A/B/C.
- Tryby: Nauka, Egzamin, Powtórki, Wszystkie.
- Filtrowanie po działach.
- Zapis postępu w `localStorage`.
- Podgląd stron PDF dla pytań z rysunkami i znakami.
- Statyczny build gotowy do GitHub Pages.

## Testy

```bash
npm run test
npm run lint
npm run build
```

## Dane

Główne dane aplikacji są w:

- `src/data/questions.json`
- `public/data/questions.json`

Skrypt `scripts/prepare_app_assets.py` aktualizuje obie kopie na podstawie roboczej bazy w `data/questions_with_answers.json`.

Do ponownego przygotowania assetów potrzebny jest Python z Pillow:

```bash
pip install -r requirements.txt
python3 scripts/prepare_app_assets.py
```
