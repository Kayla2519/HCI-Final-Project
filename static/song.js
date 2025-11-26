const messageEl = document.getElementById('message');
const resultEl = document.getElementById('result');
const albumCoverEl = document.getElementById('albumCover');
const trackNameEl = document.getElementById('trackName');
const artistNameEl = document.getElementById('artistName');
const previewPlayer = document.getElementById('previewPlayer');
const chooseAnotherBtn = document.getElementById('chooseAnother');

let currentPreview = null;

async function fetchSong() {
  messageEl.textContent = 'Loading...';
  resultEl.style.display = 'none';
  try {
    const resp = await fetch('/api/get_song');
    const data = await resp.json();
    console.log(data)
    if (!resp.ok) {
      messageEl.textContent = data.message || data.error || 'Error fetching song';
      return;
    }

    requestOptions = {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)}
    const previewResponse = await fetch('/api/get_preview', requestOptions);
    const previewData = await previewResponse.json();
    console.log(previewData)
    

    await displaySong(data, previewData);
  } catch (err) {
    messageEl.textContent = 'Network error while fetching song.';
  }
}


// function playChorusStylePreview(previewUrl) {
//     const audio = previewPlayer;

//     audio.src = previewUrl;
//     audio.currentTime = 10;
//     audio.volume = 100;
//     audio.style.display = "block";

//     audio.play().catch(() => {});

//     // Fade IN (1.5 seconds)
//     let vol = 0;
//     const fadeIn = setInterval(() => {
//         vol = Math.min(1, vol + 0.05);
//         audio.volume = vol;
//         if (vol >= 1) clearInterval(fadeIn);
//     }, 100);

//     // After 10s → fade OUT over 2s
//     setTimeout(() => {
//         let v = 1;
//         const fadeOut = setInterval(() => {
//             v = Math.max(0, v - 0.05);
//             audio.volume = v;
//             if (v <= 0) {
//                 clearInterval(fadeOut);
//                 audio.pause();
//             }
//         }, 100);
//     }, 10000); // fade-out begins at 10s

//     currentPreview = audio;
// }

async function displaySong(data, previewData) {
    messageEl.textContent = '';

    albumCoverEl.src = data.album_cover || '/static/default_cover.png';
    albumCoverEl.classList.add("glow");

    trackNameEl.textContent = data.name || 'Unknown';
    artistNameEl.textContent = data.artist || '';

    resultEl.style.opacity = 0;
        resultEl.style.display = 'block'

    // Stop previous preview
    if (currentPreview) {
        currentPreview.pause();
        currentPreview.currentTime = 0;
    }

    const waveformEl = document.getElementById("waveform");

    if (previewData.preview_url) {
        previewPlayer.src = previewData.preview_url;
        previewPlayer.currentTime = 10; // Chorus start

        // Try to play — browser may block autoplay
        previewPlayer.play().then(() => {
            // Success: show waveform
            startWaveform();
            waveformEl.style.display = "flex";
        }).catch((err) => {
            console.log(err)
            // Autoplay blocked: wait for user click
            waveformEl.style.display = "none";
            albumCoverEl.classList.remove("glow");

            messageEl.textContent = "Tap to play preview";
            messageEl.onclick = () => {
                previewPlayer.play();
                startWaveform();
                waveformEl.style.display = "flex";
                albumCoverEl.classList.add("glow");
                messageEl.textContent = "";
            };
        });

        currentPreview = previewPlayer;

    } else {
        previewPlayer.src = '';
        waveformEl.style.display = "none";
        albumCoverEl.classList.remove("glow");
    }

    setTimeout(() => {
        resultEl.style.opacity = 1;
        previewPlayer.style.display = data.preview_url ? 'block' : 'none';
    }, 120);
}



//Wave function//
function startWaveform() {
    const wf = document.getElementById("waveform");
    wf.innerHTML = "";

    for (let i = 0; i < 20; i++) {
        const bar = document.createElement("div");
        bar.className = "wave-bar";
        bar.style.animationDelay = `${i * 0.09}s`;
        wf.appendChild(bar);
    }
}


chooseAnotherBtn.addEventListener('click', (e) => {
  if (currentPreview) {
    currentPreview.pause();
    currentPreview = null;
  }
  fetchSong();
});

window.addEventListener('beforeunload', ()=> {
  if (currentPreview) currentPreview.pause();
});

document.addEventListener('DOMContentLoaded', ()=> {
  fetchSong();
});

// function playChorusStylePreview(previewUrl) {
//     const audio = previewPlayer;

//     if (!previewUrl) {
//         audio.src = "";
//         audio.style.display = "none";
//         return;
//     }

//     audio.src = previewUrl;
//     audio.currentTime = 0;
//     audio.volume = 0;
//     audio.style.display = "block";

//     audio.play().catch(()=>{});

//     // Fade in over 1.5s
//     let vol = 0;
//     const fadeIn = setInterval(() => {
//         vol = Math.min(1, vol + 0.05);
//         audio.volume = vol;
//         if (vol >= 1) clearInterval(fadeIn);
//     }, 100);

//     // Fade out after 10s, lasting 2s
//     setTimeout(() => {
//         let v = 1;
//         const fadeOut = setInterval(() => {
//             v = Math.max(0, v - 0.05);
//             audio.volume = v;
//             if (v <= 0) {
//                 clearInterval(fadeOut);
//                 audio.pause();
//             }
//         }, 100);
//     }, 10000); // start fade-out at 10s

//     //stop animation when audio finishes
//     audio.onended = () => {
//       document.getElementById("waveform").style.display = "none";
//       albumCoverEl.classList.remove("glow");
//     };
// }

