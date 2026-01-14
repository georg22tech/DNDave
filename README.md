# DMDave: Python D&D 5e Virtual Tabletop

**Repository:** [georg22tech/DNDave](https://github.com/georg22tech/DNDave)

A lightweight, browser-based Virtual Tabletop (VTT) and Campaign Manager for Dungeons & Dragons 5th Edition. Built with **Python**, **Flask**, and **Socket.IO**, it allows Dungeon Masters to manage initiative and monsters while players build characters and roll dice in real-time.

## 🚀 Features

### For the Dungeon Master
* **Multi-Campaign Support:** Create and manage multiple isolated campaigns.
* **Campaign Lobby:** Generate unique **Join Codes** and links for players.
* **Initiative Tracker:** * Add players and monsters effortlessly.
    * Search the **D&D 5e API** for monsters and add them instantly.
    * Create **Custom Monsters** with editable stats, skills, and actions directly in the UI.
* **Roll Log:** View every roll made by players in real-time.
* **Private Rolls:** Toggle "Secret Roll" to hide DM rolls from players.
* **Custom Dice Bar:** Quick-roll specific dice counts (e.g., 4d6 + 2) directly from the bottom of the screen.
* **Reference Tool:** Look up Spells and Monster Stat Blocks on the fly.

### For Players
* **Character Builder:**
    * 6-step wizard (Identity, Stats, Class, Skills, Equipment, Spells).
    * **Automatic Spell Lists:** Filters spells based on Class and Level using local game rules.
    * **Equipment Search:** Integrated API search for weapons and armor.
* **Interactive Character Sheet:**
    * Click-to-roll Attacks, Checks, and Saves.
    * Track HP, Spell Slots, and Class Resource Charges.
    * Real-time inventory management.
* **Mobile Friendly:** Works on phone browsers for IRL sessions.

## 🛠️ Prerequisites

* **Python 3.x** installed on your machine.
* **Node.js** (Optional, required only if you plan to host for remote players via LocalTunnel).

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/georg22tech/DNDave.git](https://github.com/georg22tech/DNDave.git)
    cd DNDave
    ```

2.  **Install Python dependencies:**
    You need Flask and Flask-SocketIO. Run the following command:
    ```bash
    pip install flask flask-socketio
    ```

3.  **Ensure File Structure:**
    Your folder should look like this:
    ```
    /DNDave
    ├── DMDave.py           # The main server file
    ├── game_rules.py       # Local database of Races, Classes, and Spells
    └── templates/          # HTML files (lobby, builder, sheet, dm)
    ```

## 🎮 How to Run Locally (Same Wi-Fi)

1.  **Start the Server:**
    Open your terminal or command prompt in the project folder and run:
    ```bash
    python DMDave.py
    ```

2.  **Access:**
    * **DM (You):** Open your browser to `http://127.0.0.1:5000`.
    * **Players:** Find your computer's Local IP address (Command Prompt: `ipconfig` or Terminal: `ifconfig`). Players enter `http://YOUR_IP:5000` on their phones/laptops.

---

## 🌍 Remote Play (Play over the Internet)

If your players are **not** on the same Wi-Fi, you must expose your local server to the internet. The easiest way to do this for free is using **LocalTunnel**.

### Step 1: Install LocalTunnel
You will need Node.js installed for this. In your terminal, run:
```bash
npm install -g localtunnel
