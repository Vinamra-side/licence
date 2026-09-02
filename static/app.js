const $ = (selector) => document.querySelector(selector);
let token = localStorage.getItem("licence-owner-token") || "";
let registration = null;

async function api(path, options = {}) {
  options.headers = {"Content-Type": "application/json", ...(token ? {Authorization: `Bearer ${token}`} : {})};
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw Error(data.error || "Request failed");
  return data;
}

function openView(name) {
  const copy = {
    dashboard: ["Licence Dashboard", "Monitor access and seats."],
    licence: ["Licence Settings", "Control application access and seat limits."],
    updates: ["Updates", "Keep this application current."]
  };
  document.querySelectorAll("[data-page]").forEach((page) => page.classList.toggle("hidden", page.dataset.page !== name));
  document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  $("#pageTitle").textContent = copy[name][0];
  $("#pageSubtitle").textContent = copy[name][1];
}

document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => openView(button.dataset.view)));

function showApp() {
  $("#login").classList.add("hidden");
  $("#app").classList.remove("hidden");
  loadLicence();
}

async function loadLicence() {
  try {
    const data = await api("/api/license");
    const seats = data.seats;
    $("#active").textContent = seats.active;
    $("#available").textContent = Math.max(0, seats.limit - seats.active);
    $("#status").textContent = data.is_active ? "Active" : "Paused";
    $("#rowStatus").textContent = data.is_active ? "Active" : "Paused";
    $("#seats").textContent = `${seats.active} / ${seats.limit}`;
    $("#enabled").checked = data.is_active;
    $("#limit").value = data.max_users;
    $("#note").value = data.note || "";
  } catch (error) {
    localStorage.removeItem("licence-owner-token");
    location.reload();
  }
}

$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await api("/api/login", {method: "POST", body: JSON.stringify({username: $("#username").value, password: $("#password").value})});
    token = data.token;
    localStorage.setItem("licence-owner-token", token);
    showApp();
  } catch (error) { $("#loginError").textContent = error.message; }
});

$("#licenceForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/license", {method: "PUT", body: JSON.stringify({is_active: $("#enabled").checked, max_users: Number($("#limit").value), note: $("#note").value})});
    $("#saved").textContent = "Saved and applied immediately.";
    await loadLicence();
  } catch (error) { $("#saved").textContent = error.message; }
});

$("#logout").addEventListener("click", () => { localStorage.removeItem("licence-owner-token"); location.reload(); });
$("#checkUpdates").addEventListener("click", async () => {
  $("#updateStatus").textContent = "Checking for updates...";
  if (registration) await registration.update();
  $("#updateStatus").textContent = registration && registration.waiting ? "An update is ready." : "This application is up to date.";
});
if (token) showApp();

if ("serviceWorker" in navigator) addEventListener("load", () => {
  let refreshing = false;
  navigator.serviceWorker.register("/service-worker.js").then((value) => {
    registration = value;
    const prompt = (worker) => {
      if (!worker || document.querySelector(".toast")) return;
      const toast = document.createElement("div");
      toast.className = "toast";
      toast.innerHTML = '<span><b>Licence app update available</b><br><small>Reload to apply it without reinstalling.</small></span><button>Update now</button>';
      toast.querySelector("button").onclick = () => worker.postMessage({type: "SKIP_WAITING"});
      document.body.append(toast);
    };
    if (registration.waiting) prompt(registration.waiting);
    registration.onupdatefound = () => {
      const worker = registration.installing;
      worker.onstatechange = () => { if (worker.state === "installed" && navigator.serviceWorker.controller) prompt(worker); };
    };
    setInterval(() => registration.update(), 900000);
  });
  navigator.serviceWorker.oncontrollerchange = () => { if (!refreshing) { refreshing = true; location.reload(); } };
});
