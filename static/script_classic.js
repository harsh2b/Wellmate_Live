
// At the top of script_classic.js
document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.includes("/static/patient_form_classic.html")) {
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = localStorage.getItem("sessionId");
        console.log("Checking sessionId on patient form:", sessionId);
        if (!sessionId) {
            console.warn("No sessionId found, redirecting to login");
            window.location.href = "/static/login_classic.html";
        }
    }
});


let sessionId = null;
const apiUrl = "http://localhost:8000"; // Update this to your actual API URL
const botAvatar = "/static/cropped_image.webp";
const userAvatar = "/static/user_avatar_placeholder.png";

let currentConversation = { timestamp: Date.now(), messages: [] };
let pastConsultations = JSON.parse(localStorage.getItem("pastConsultations")) || [];

console.log("Script loaded, apiUrl:", apiUrl); // Debug

// Handle Guest Login
document.getElementById("guest-login-btn")?.addEventListener("click", () => {
    const guestSessionId = "guest-" + Date.now();
    console.log("Guest login, setting sessionId:", guestSessionId); // Debug
    localStorage.setItem("sessionId", guestSessionId);
    localStorage.setItem("isGuest", "true");
    window.location.href = "/static/patient_form_classic.html";
});

// Handle patient form with autofill and validation
document.getElementById("patient-info")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const patientInfo = {
        name: document.getElementById("patient-name").value.trim(),
        age: parseInt(document.getElementById("patient-age").value) || 0,
        gender: document.getElementById("patient-gender").value,
        language: document.getElementById("patient-language").value,
        phone: document.getElementById("patient-phone").value.trim() || ""
    };
    console.log("Submitting patient info:", patientInfo); // Debug

    if (!patientInfo.name || patientInfo.age <= 0) {
        console.warn("Invalid patient info: name or age missing"); // Debug
        alert("Please provide a valid name and age.");
        return;
    }

    localStorage.setItem("patientInfo", JSON.stringify(patientInfo));
    sessionId = localStorage.getItem("sessionId");
    console.log("Session ID for patient info submission:", sessionId); // Debug
    if (sessionId) {
        try {
            const response = await fetch(`${apiUrl}/update-patient`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId, patient_info: patientInfo })
            });
            console.log("Update patient response status:", response.status); // Debug
            const data = await response.json();
            console.log("Update patient response data:", data); // Debug
            if (data.status !== "success") {
                throw new Error("Failed to update patient info on server");
            }
        } catch (error) {
            console.error("Error updating patient info:", error); // Debug
            alert("Failed to save patient info on server. Proceeding with local data.");
        }
    } else {
        console.warn("No sessionId found. Proceeding with local data."); // Debug
    }
    window.location.href = "/static/chat_classic.html";
});

// Autofill patient form if data exists
if (window.location.pathname.includes("/static/patient_form_classic.html")) {
    const patientInfo = JSON.parse(localStorage.getItem("patientInfo")) || {};
    console.log("Autofilling patient form with:", patientInfo); // Debug
    document.getElementById("patient-name").value = patientInfo.name || "";
    document.getElementById("patient-age").value = patientInfo.age || "";
    document.getElementById("patient-gender").value = patientInfo.gender || "Male";
    document.getElementById("patient-language").value = patientInfo.language || "English";
    document.getElementById("patient-phone").value = patientInfo.phone || "";
}

// Load profile data
if (window.location.pathname.includes("/static/profile_classic.html")) {
    const patientInfo = JSON.parse(localStorage.getItem("patientInfo")) || {};
    console.log("Loading profile with:", patientInfo); // Debug
    document.getElementById("profile-name").textContent = patientInfo.name || "N/A";
    document.getElementById("profile-age").textContent = patientInfo.age || "N/A";
    document.getElementById("profile-gender").textContent = patientInfo.gender || "N/A";
    document.getElementById("profile-language").textContent = patientInfo.language || "N/A";
    document.getElementById("profile-phone").textContent = patientInfo.phone || "N/A";
    document.getElementById("profile-session").textContent = localStorage.getItem("sessionId") ? "Active Session" : "No Active Session";
    updateSidebar();
}

// Load chat and profile functionality
if (window.location.pathname.includes("/static/chat_classic.html") || window.location.pathname.includes("/static/profile_classic.html")) {
    document.addEventListener("DOMContentLoaded", () => {
        sessionId = localStorage.getItem("sessionId");
        console.log("Session ID on page load:", sessionId); // Debug
        if (!sessionId && window.location.pathname.includes("/static/chat_classic.html")) {
            console.warn("No sessionId found, redirecting to login"); // Debug
            alert("No session found. Please log in or start as a guest.");
            window.location.href = "/static/login_classic.html";
        }

        // Toggle sidebar
        document.getElementById("menu-toggle")?.addEventListener("click", () => {
            console.log("Toggling sidebar"); // Debug
            document.querySelector(".sidebar").classList.toggle("active");
        });

        // Removed updateSidebar() call here as chat history is no longer displayed

        if (window.location.pathname.includes("/static/chat_classic.html")) {
            setTimeout(() => {
                const chatMessages = document.getElementById("chat-messages");
                if (!chatMessages) {
                    console.error("Chat messages container not found"); // Debug
                    return;
                }
                console.log("Number of chat messages:", document.querySelectorAll(".chat-message").length); // Debug
                if (document.querySelectorAll(".chat-message").length === 0) {
                    addMessage("assistant", "Hello! I\'m Dr. Black, a physician with 30 years of experience. How may I help you today? 😊");
                }
            }, 500);
        }
    });
}

// Chat functionality
document.getElementById("send-button")?.addEventListener("click", sendChatMessage);
document.getElementById("user-input")?.addEventListener("keypress", async (e) => {
    if (e.key === "Enter") sendChatMessage();
});

async function sendChatMessage() {
    const userInput = document.getElementById("user-input").value.trim();
    console.log("Sending message:", userInput, "with sessionId:", sessionId); // Debug
    if (!userInput || !sessionId) {
        console.warn("Invalid input or sessionId:", userInput, sessionId); // Debug
        alert("Please enter a message and ensure you are logged in.");
        return;
    }

    addMessage("user", userInput);
    document.getElementById("user-input").value = "";

    try {
        const response = await fetch(`${apiUrl}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message: userInput })
        });
        console.log("Chat response status:", response.status); // Debug
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log("Chat response data:", data); // Debug
        const botResponse = data.response;
        addMessage("assistant", botResponse);

        // Removed local chat history storage as it's now handled by Supabase
        // currentConversation.messages.push({ role: "user", content: userInput });
        // currentConversation.messages.push({ role: "assistant", content: botResponse });

        // Removed logic for saving past consultations to localStorage
        // if (userInput.toLowerCase().includes("start new conversation") || window.performance.navigation.type === 1) {
        //     if (currentConversation.messages.length > 0) {
        //         pastConsultations.push({ ...currentConversation });
        //         console.log("Saved conversation:", currentConversation); // Debug
        //         currentConversation = { timestamp: Date.now(), messages: [] };
        //         localStorage.setItem("pastConsultations", JSON.stringify(pastConsultations));
        //         updateSidebar();
        //         document.getElementById("chat-messages").innerHTML = "";
        //         addMessage("assistant", "Hello! I\'m Dr. Black, a physician with 30 years of experience. How may I help you today? 😊");
        //     }
        // }
        // Removed updateSidebar() call here as chat history is no longer displayed
    } catch (error) {
        console.error("Error in sendChatMessage:", error); // Debug
        alert("Failed to send message: " + error.message);
    }
}

function convertMarkdownToHTML(text) {
    text = text.replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");
    text = text.replace(/\*(.*?)\*/g, "<i>$1</i>");
    return text;
}

function addMessage(role, content) {
    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) {
        console.error("Chat messages container not found"); // Debug
        return;
    }
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("chat-message");
    const avatar = role === "user" ? userAvatar : botAvatar;
    const formattedContent = convertMarkdownToHTML(content);
    messageDiv.innerHTML = `<img src="${avatar}" width="30" height="30"> <div>${formattedContent}</div>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Removed loadConsultation function as chat history is no longer displayed
// function loadConsultation(messages) {
//     const chatMessages = document.getElementById("chat-messages");
//     if (!chatMessages) {
//         console.error("Chat messages container not found"); // Debug
//         return;
//     }
//     chatMessages.innerHTML = "";
//     messages.forEach(msg => addMessage(msg.role, msg.content));
//     currentConversation = { timestamp: Date.now(), messages: [...messages] };
// }

// Removed updateSidebar function as chat history is no longer displayed
function updateSidebar() {
    // This function is now empty as chat history is no longer displayed in the sidebar.
    // The sidebar navigation items are still handled by their respective event listeners.
}

// Removed deleteCurrentConversation function as chat history is no longer displayed
// function deleteCurrentConversation() {
//     console.log("Deleting current conversation"); // Debug
//     const confirmDelete = confirm(`Are you sure you want to delete the current conversation? This action cannot be undone.`);
//     if (!confirmDelete) return;

//     currentConversation = { timestamp: Date.now(), messages: [] };
//     updateSidebar();
//     const chatMessages = document.getElementById("chat-messages");
//     if (chatMessages) {
//         chatMessages.innerHTML = "";
//         if (document.querySelectorAll(".chat-message").length === 0) {
//             addMessage("assistant", "Hello! I\'m Dr. Black, a physician with 30 years of experience. How may I help you today? 😊");
//         }
//     }
//     alert("Current conversation deleted successfully");
// }

// Removed deleteConsultation function as chat history is no longer displayed
// function deleteConsultation(index) {
//     console.log("Deleting consultation:", index); // Debug
//     const confirmDelete = confirm(`Are you sure you want to delete Consultation ${index + 1}? This action cannot be undone.`);
//     if (!confirmDelete) return;

//     pastConsultations.splice(index, 1);
//     localStorage.setItem("pastConsultations", JSON.stringify(pastConsultations));
//     updateSidebar();
//     const chatMessages = document.getElementById("chat-messages");
//     if (chatMessages) {
//         chatMessages.innerHTML = "";
//         if (document.querySelectorAll(".chat-message").length === 0) {
//             addMessage("assistant", "Hello! I\'m Dr. Black, a physician with 30 years of experience. How may I help you today? 😊");
//         }
//     }
//     alert("Consultation deleted successfully");
// }

function logout() {
    console.log("Logging out, clearing sessionId"); // Debug
    localStorage.removeItem("sessionId");
    localStorage.removeItem("isGuest");
    localStorage.removeItem("patientInfo");
    window.location.href = "/static/login_classic.html";
}

function newChat() {
    console.log("Starting new chat"); // Debug
    window.location.href = "/static/patient_form_classic.html";
}



