# 📥 YouTube Downloader (Flask + yt-dlp)

A web-based YouTube video/audio downloader built with **Flask** and **yt-dlp**, providing a simple UI for downloading public YouTube videos as MP4 or MP3.

---

## 📸 Demo Preview

Video Info Page                      

![YOUTUBE_DOWNLOADER](screenshots/yt.png) | 


## 🔧 Technical Overview

This Flask application uses [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) for downloading YouTube content. It allows:

### 📦 Features
  🎞 MP4 & MP3 download support
  
  🆓 Public video support only (on hosted version)
  
  🖼 Metadata preview (thumbnail, title, duration)
  
  📊 Real-time progress bar
  
  🧹 Auto-delete downloaded files after delivery

---

## ⚙️ Stack

| Layer       | Tech Used          |
|-------------|--------------------|
| Backend     | Flask (Python)     |
| Downloader  | yt-dlp             |
| Audio Convert | FFmpeg           |
| Frontend    | HTML, CSS, JavaScript |
| Deployment  | [Render.com](https://render.com) + Gunicorn |

---

This live version is **limited to public YouTube videos only**. It **does not support login-based videos** due to lack of authentication.

Videos that will **not** work include:

### 🚧 Limitations

- 🔞 Age-restricted content
- 🔒 Private videos
- 🌍 Region-locked videos
- 🙃 Videos requiring login

You'll see an error like: "**This video requires login. Please try a different public video.**"
---------

## ✅ FOR Full Access (Run Locally)

To support restricted videos, run the app **locally**:

###  1. Clone the Project

```
bash
git clone https://github.com/your-username/your-repo.git
cd your-repo 
```

### 2. Set Up the Environment
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.Run the App
 ```
python app.py
 ```


### 👨‍💻 Contributors

Want to contribute?

🍴 Fork and clone this repo

🧪 Run locally

🎯 Add support (e.g., Add playlist download)

📬 Open a pull request
 
