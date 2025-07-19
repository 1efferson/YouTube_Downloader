
      // URL Input Handler
      async function handleUrlInput(e) {
        const url = e.target.value.trim();
        currentDownload.url = url;

        const videoId = extractVideoId(url);
        const thumbnail = document.getElementById("video-thumbnail");
        const titleElement = document.getElementById("video-title");
        const errorElement = document.getElementById("error-message");

        if (videoId) {
          thumbnail.style.display = "block";
          thumbnail.src = "";
          titleElement.textContent = "Loading...";
          errorElement.style.display = "none";

          try {
            const response = await fetch("/get_info", {
              method: "POST",
              headers: {
                "Content-Type": "application/x-www-form-urlencoded",
              },
              body: `url=${encodeURIComponent(url)}`,
            });

            const data = await response.json();

            if (data.status === "success") {
              // Ensure the thumbnail is loaded directly from YouTube
              const imageUrl = data.thumbnail.startsWith("http")
                ? data.thumbnail
                : `${window.location.origin}/${data.thumbnail}`;

              thumbnail.src = imageUrl;
              titleElement.textContent = data.title;
              document.getElementById("download-btn").disabled = false;

              // Store metadata
              thumbnail.dataset.videoId = data.video_id;
              titleElement.dataset.cleanTitle = sanitizeFilename(data.title);
              currentDownload.videoId = data.video_id;
            } else {
              showError(data.message);
            }
          } catch (error) {
            showError("Failed to fetch video info: " + error.message);
          }
        } else {
          thumbnail.style.display = "none";
          titleElement.textContent = "";
          document.getElementById("download-btn").disabled = true;
          currentDownload.videoId = "";
        }
      }

      window.addEventListener("DOMContentLoaded", function () {
        const urlInput = document.getElementById("url-input");
        if (urlInput) {
          urlInput.addEventListener("input", handleUrlInput);
        }
      });

      // resets UI when user clicks clear
      function clearInputManually() {
        const progressBar = document.getElementById("download-progress");
        const urlInput = document.getElementById("url-input");
        const titleElement = document.getElementById("video-title");
        const thumbnail = document.getElementById("video-thumbnail");
        const downloadBtn = document.getElementById("download-btn");

        if (urlInput) urlInput.value = "";
        if (titleElement) titleElement.textContent = "";
        if (thumbnail) {
          thumbnail.src = "";
          thumbnail.style.display = "none";
        }
        if (progressBar) {
          progressBar.style.width = "0%";
          progressBar.textContent = "0%";
          progressBar.style.backgroundColor = "";
        }
        if (downloadBtn) downloadBtn.disabled = true;
      }

      window.addEventListener("DOMContentLoaded", function () {
        const clearBtn = document.getElementById("clear-btn");
        if (clearBtn) {
          clearBtn.addEventListener("click", clearInputManually);
        }
      });
      // ==============================================
      // GLOBAL VARIABLES
      // ==============================================
      let progressEventSource = null;
      let currentDownload = {
        url: "",
        format: "mp4",
        videoId: "",
      };

      // ==============================================
      // INITIALIZATION - EVENT LISTENERS
      // ==============================================
      document.addEventListener("DOMContentLoaded", function () {
        // URL input handler
        document
          .getElementById("url-input")
          .addEventListener("input", handleUrlInput);

        // Download button handler
        document
          .getElementById("download-btn")
          .addEventListener("click", startDownload);

        // Format selection handler
        document.querySelectorAll('input[name="format"]').forEach((radio) => {
          radio.addEventListener("change", function () {
            currentDownload.format = this.value;
          });
        });
      });

      // ==============================================
      // PROGRESS TRACKING FUNCTIONS (ADD THIS SECTION)
      // ==============================================
      function setupProgressListener(videoId) {
        if (progressEventSource) {
          progressEventSource.close();
        }

        progressEventSource = new EventSource(`/progress/${videoId}`);
        const progressBar = document.getElementById("download-progress");

        progressBar.style.transition = "width 0.3s ease";
        progressBar.style.width = "0%";
        progressBar.textContent = "0%";

        progressEventSource.onmessage = function (event) {
          const data = JSON.parse(event.data);
          const progress = Math.round(data.progress);

          progressBar.style.width = `${progress}%`;
          progressBar.textContent = `${progress}%`;

          if (data.completed) {
            progressEventSource.close();
            if (progress === 100) {
              progressBar.style.backgroundColor = "#4CAF50";
              addToRecentDownloads();
            } else {
              progressBar.style.backgroundColor = "#f44336";
            }
          }
        };

        progressEventSource.onerror = function () {
          console.error("Progress updates disconnected");
          progressBar.style.backgroundColor = "#f44336";
          progressEventSource.close();
        };
      }

      async function startDownload() {
        if (!validateDownload()) return;

        const { url, format, videoId } = currentDownload;
        const progressBar = document.getElementById("download-progress");
        const btn = document.getElementById("download-btn");

        resetDownloadUI();
        setupProgressListener(videoId);

        try {
          const response = await fetch(
            `/download?url=${encodeURIComponent(
              url
            )}&download_type=${format}&video_id=${videoId}`
          );

          if (!response.ok) {
            throw new Error(await response.text());
          }

          await handleDownloadResponse(response, format);
        } catch (error) {
          handleDownloadError(error);
        } finally {
          btn.disabled = false;
          btn.textContent = "Download";
        }
      }

      // ==============================================
      // URL INPUT HANDLER
      // ==============================================
      async function handleUrlInput(e) {
        const url = e.target.value.trim();
        currentDownload.url = url;

        const videoId = extractVideoId(url);
        const thumbnail = document.getElementById("video-thumbnail");
        const titleElement = document.getElementById("video-title");
        const errorElement = document.getElementById("error-message");

        if (videoId) {
          // Show loading state
          thumbnail.style.display = "block";
          thumbnail.src = "";
          titleElement.textContent = "Loading...";
          errorElement.style.display = "none";

          try {
            const response = await fetch("/get_info", {
              method: "POST",
              headers: {
                "Content-Type": "application/x-www-form-urlencoded",
              },
              body: `url=${encodeURIComponent(url)}`,
            });

            const data = await response.json();

            if (data.status === "success") {
              thumbnail.src = data.thumbnail;
              thumbnail.style.display = "block";
              titleElement.textContent = data.title;
              document.getElementById("download-btn").disabled = false;

              thumbnail.dataset.videoId = data.video_id;
              titleElement.dataset.cleanTitle = sanitizeFilename(data.title);
              currentDownload.videoId = data.video_id;
            } else {
              showError(data.message);
            }
          } catch (error) {
            showError("Failed to fetch video info: " + error.message);
          }
        } else {
          // Invalid URL or no video ID found
          thumbnail.style.display = "none";
          titleElement.textContent = "";
          document.getElementById("download-btn").disabled = true;
          currentDownload.videoId = "";
        }
      }

      // ==============================================
      // DOWNLOAD FUNCTIONS
      // ==============================================
      async function startDownload() {
        if (!validateDownload()) return;

        const { url, format, videoId } = currentDownload;
        const progressBar = document.getElementById("download-progress");
        const btn = document.getElementById("download-btn");

        // Reset UI state
        resetDownloadUI();

        // Start progress tracking
        setupProgressListener(videoId);

        try {
          // Initiate the download
          const response = await fetch(
            `/download?url=${encodeURIComponent(
              url
            )}&download_type=${format}&video_id=${videoId}`
          );

          if (!response.ok) {
            throw new Error(await response.text());
          }

          // Handle the downloaded file
          await handleDownloadResponse(response, format);
        } catch (error) {
          handleDownloadError(error);
        }
      }

      function setupProgressListener(videoId) {
        // Close existing connection if any
        if (progressEventSource) {
          progressEventSource.close();
        }

        // Create new EventSource connection
        progressEventSource = new EventSource(`/progress/${videoId}`);
        const progressBar = document.getElementById("download-progress");

        progressEventSource.onmessage = function (event) {
          const data = JSON.parse(event.data);

          // Update progress bar
          const progress = Math.round(data.progress);
          progressBar.style.width = `${progress}%`;
          progressBar.textContent = `${progress}%`;

          // Handle completion
          if (data.completed) {
            progressEventSource.close();
            if (progress === 100) {
              addToRecentDownloads();
            }
          }
        };

        progressEventSource.onerror = function () {
          console.error("Progress updates disconnected");
          progressEventSource.close();
          showError("Connection to progress updates lost");
        };
      }

      async function handleDownloadResponse(response, format) {
        const contentDisposition = response.headers.get("content-disposition");
        const titleElement = document.getElementById("video-title");

        // Determine filename
        let filename = `${
          titleElement.dataset.cleanTitle || "download"
        }.${format}`;
        if (contentDisposition) {
          filename = contentDisposition.split("filename=")[1].replace(/"/g, "");
        }

        // Create download link and trigger download
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();

        // Cleanup
        setTimeout(() => {
          document.body.removeChild(a);
          window.URL.revokeObjectURL(downloadUrl);
          resetDownloadButton();
          resetAfterDownload(); // <- add this line
        }, 100);
      }

      // ==============================================
      // UI MANAGEMENT FUNCTIONS
      // ==============================================
      function resetDownloadUI() {
        const progressBar = document.getElementById("download-progress");
        progressBar.style.width = "0%";
        progressBar.textContent = "0%";
        document.getElementById("error-message").style.display = "none";
        document.getElementById("download-btn").disabled = true;
        document.getElementById("download-btn").textContent = "Downloading...";
      }

      function resetDownloadButton() {
        const btn = document.getElementById("download-btn");
        btn.disabled = false;
        btn.textContent = "Download";
      }

      function handleDownloadError(error) {
        const progressBar = document.getElementById("download-progress");
        progressBar.style.backgroundColor = "#f44336";
        showError("Download failed: " + error.message);

        if (progressEventSource) {
          progressEventSource.close();
        }
        resetDownloadButton();
      }

      // ==============================================
      // HELPER FUNCTIONS
      // ==============================================
      function validateDownload() {
        if (!currentDownload.url || !currentDownload.videoId) {
          showError("Please enter a valid YouTube URL first");
          return false;
        }
        return true;
      }

      function extractVideoId(url) {
        const regExp =
          /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
        const match = url.match(regExp);
        return match && match[2].length === 11 ? match[2] : null;
      }

      function sanitizeFilename(title) {
        return title.replace(/[^\w\s-]/g, "").replace(/\s+/g, "_");
      }

      function showError(message) {
        const errorElement = document.getElementById("error-message");
        errorElement.textContent = message;
        errorElement.style.display = "block";

        setTimeout(() => {
          errorElement.style.display = "none";
        }, 5000);
      }

      function addToRecentDownloads() {
        const thumbnail = document.getElementById("video-thumbnail");
        const titleElement = document.getElementById("video-title");
        const format = document.querySelector(
          'input[name="format"]:checked'
        ).value;
        const url = document.getElementById("url-input").value.trim();
        const container = document.getElementById("recent-downloads");

        // Remove empty state if present
        if (container.querySelector(".empty-state")) {
          container.innerHTML = "";
        }

        // Create new download item
        const item = document.createElement("div");
        item.className = "download-item";
        item.innerHTML = `
                  <img src="${thumbnail.src}" alt="${titleElement.textContent}">
                  <div class="info">
                      <div class="title">${titleElement.textContent}</div>
                      <div class="format">${format.toUpperCase()}</div>
                  </div>
                  <a class="action" href="/download?url=${encodeURIComponent(
                    url
                  )}&download_type=${format}" download>
                      <svg viewBox="0 0 24 24" width="24" height="24">
                          <path fill="currentColor" d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z" />
                      </svg>
                      Again
                  </a>
              `;

        // Add to top of recent downloads
        container.prepend(item);

        // Add this function to your JavaScript section
        function resetAfterDownload() {
          const progressBar = document.getElementById("download-progress");
          const urlInput = document.getElementById("url-input");
          const titleElement = document.getElementById("video-title");
          const thumbnail = document.getElementById("video-thumbnail");

          // Reset progress bar
          progressBar.style.width = "0%";
          progressBar.textContent = "0%";
          progressBar.style.backgroundColor = "";

          // Clear input and video info
          urlInput.value = "";
          titleElement.textContent = "";
          thumbnail.src = "";
          thumbnail.style.display = "none";

          // Disable download button
          document.getElementById("download-btn").disabled = true;
        }
      }
   