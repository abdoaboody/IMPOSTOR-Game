# 🎭 Impostor Game

A multiplayer social deduction game where players must work together, uncover the impostor, and avoid being deceived.

## 🌐 About the Game

**Impostor Game** is a browser-based multiplayer party game designed for friends and groups.

Players join a room using a room code. Each player receives a secret role, and one player becomes the impostor. While everyone else knows the secret word or topic, the impostor must blend in, gather clues, and avoid being exposed.

The goal is simple: identify the impostor before they figure out the secret.

## 🎮 How to Play

1. **Create a Room** – One player creates a game room.
2. **Invite Friends** – Share the room code with other players.
3. **Join the Game** – Players enter the room and wait for the host to start.
4. **Discover Your Role** – Each player receives their secret information privately.
5. **Discuss and Investigate** – Players take turns giving clues and discussing their suspicions.
6. **Find the Impostor** – Vote for the player you believe is the impostor.
7. **Win the Game** – The regular players win by identifying the impostor, while the impostor wins by successfully deceiving everyone.

## ✨ Features

- Real-time multiplayer gameplay.
- Private game rooms with unique room codes.
- Secret roles and hidden information.
- Interactive player voting.
- Live updates using WebSockets.
- Profession-based game content.
- Browser-based experience with no installation required.
- Mobile-friendly interface.
- Add-to-home-screen support on compatible devices.
- Custom "Cartoon Neo-Pop" visual identity with bundled fonts (no external requests).
- Bilingual interface: Arabic (default, RTL) and Italian (LTR) with a one-tap language toggle on the home screen; the choice is remembered per device.

## 🖥️ Website Experience

The website is designed to make playing with friends simple and accessible.

- **Home Page:** Create a new room or join an existing one.
- **Waiting Room:** See who has joined before the game starts.
- **Game Interface:** View your role and participate in the game.
- **Voting System:** Choose who you think the impostor is.
- **Results:** Discover the outcome of the round.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main application logic |
| Flask | Web framework |
| Flask-SocketIO | Real-time communication |
| JavaScript | Interactive frontend |
| HTML5 | Website structure |
| CSS3 | Styling and responsive layout |
| Gunicorn | Production application server |
| Render | Hosting and deployment |

## 📁 Project Structure

```text
impostor-game/
│
├── static/
│   ├── css/
│   ├── fonts/          # Baloo Bhaijaan 2 + Rubik, bundled locally (OFL)
│   ├── js/
│   └── icons/
│
├── templates/
│   ├── index.html
│   └── room.html
│
├── tests/
│   ├── test_game.py
│   └── test_socket.py
│
├── app.py
├── game_logic.py
├── professions.py
├── room_manager.py
├── socket_events.py
├── requirements.txt
└── render.yaml
```

## 🎨 Design & Languages

- **Visual identity:** deep petrol-night base with neon party accents
  (crimson `#FF2A6D`, cyan `#00E5FF`, green `#38EF7D`, yellow `#FFD166`),
  chunky cartoon borders and hard shadows, playful mascot and micro-animations.
- **Fonts:** Baloo Bhaijaan 2 (headings) and Rubik (body) ship inside
  `static/fonts/` and load via `static/css/fonts.css` — the game makes **no
  requests to font CDNs**. Socket.IO's client is also served locally from
  `static/js/socket.io.min.js`.
- **Languages:** Arabic is the default (RTL). The globe button on the home
  screen switches everything to Italian (LTR); the choice is stored in
  `localStorage` (`impostor:lang`) and restored on the next visit. All layout
  uses CSS logical properties so both directions render correctly.
- **Credit card:** a small GitHub icon at the bottom expands (animated) into the "created by Aboody" card with the GitHub link; tapping it again collapses it. It lives
  in the normal document flow at the bottom of every page — it is never
  fixed-positioned and never covers content while scrolling.

## 🚀 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/impostor-game.git
cd impostor-game
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

**Windows:**

```bash
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python app.py
```

Open your browser at:

```text
http://127.0.0.1:5000
```

## 🧪 Tests

Run the automated tests with:

```bash
pytest
```

## ☁️ Deployment

The project is configured for deployment on [Render](https://render.com/) using the included `render.yaml` configuration.

## 📌 Notes

- The game is designed for real-time multiplayer sessions.
- Room state is maintained in application memory.
- The current deployment configuration uses a single Gunicorn worker to keep room state consistent.
- Free hosting services may temporarily sleep after periods of inactivity.

---

**Made for fun, deception, and unforgettable moments with friends. 🎭**