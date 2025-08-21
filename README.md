# 🎬 MovieMan

**MovieMan** is a desktop application powered by **OpenAI GPT** and the **OMDb API** that helps you discover movies tailored to your mood and preferences.  
With a simple and elegant **Tkinter GUI**, you can explore movie recommendations, view posters and details, and decide whether it’s a **Smash ✅** or **Pass ❌**.

---

## ✨ Key Features

- 🤖 **AI-Driven Recommendations** – GPT suggests movies based on your input.
- 🎞️ **Movie Details & Posters** – fetched in real time from the OMDb API.
- 🎨 **Light & Dark Mode** – toggle between modern themes.
- ⚡ **Smooth UX** – threaded API calls prevent the UI from freezing.
- 👍 **Interactive Flow** – like or skip movies until you find the perfect match.

---

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/movieman.git
cd movieman
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

**requirements.txt**
```
openai
requests
pillow
```

### 3. Configure API keys
Create a `config.json` file in the project root with your API credentials:

```json
{
  "openai_api_key": "your_openai_api_key",
  "omdb_api_key": "your_omdb_api_key"
}
```

- Get an [OpenAI API Key](https://platform.openai.com/).  
- Get an [OMDb API Key](https://www.omdbapi.com/apikey.aspx).  

⚠️ **Important:** Do not commit `config.json` to GitHub. Add it to your `.gitignore`.

---

## 🚀 Usage

Run the application:

```bash
python main.py
```

1. Enter your mood or movie preference.  
2. Click **Recommend** → AI suggests a movie.  
3. Movie title, year, plot, and poster will be displayed.  
4. Choose:
   - ✅ **Smash** → accept the recommendation.  
   - ❌ **Pass** → get another suggestion.  

---

## 📂 Project Structure

```
movieman/
│── main.py          # Tkinter application entry point
│── config.json      # API keys (excluded from version control)
│── requirements.txt # Python dependencies
│── README.md        # Documentation
```

---

## 📸 Screenshots

*(Add screenshots or a demo GIF here to showcase the UI)*

---

## 💡 Roadmap

- [ ] Add support for multiple recommendations at once  
- [ ] Enable session history and restart without quitting  
- [ ] Improve UI layout with ttk styling and responsiveness  
- [ ] Cache posters locally to reduce API calls  

---

## 📜 License

This project is licensed under the **MIT License**.  
Feel free to use, modify, and distribute.

---

## 🙌 Acknowledgements

- [OpenAI](https://openai.com/) – for the GPT model powering recommendations.  
- [OMDb API](https://www.omdbapi.com/) – for movie data and posters.  
- [Python Tkinter](https://docs.python.org/3/library/tkinter.html) – for the GUI framework.
