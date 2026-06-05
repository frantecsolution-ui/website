const menuBtn = document.querySelector(".menu-btn");
const menu = document.querySelector(".menu");

if (menuBtn && menu) {
  menuBtn.addEventListener("click", () => {
    menu.classList.toggle("open");
  });
}

const year = document.querySelectorAll(".year");
year.forEach((el) => {
  el.textContent = String(new Date().getFullYear());
});

const contactForm = document.querySelector("#contactForm");
const contactStatus = document.querySelector("#contactStatus");

if (contactForm && contactStatus) {
  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(contactForm);
    const payload = {
      name: (formData.get("name") || "").toString().trim(),
      email: (formData.get("email") || "").toString().trim(),
      message: (formData.get("message") || "").toString().trim(),
    };

    contactStatus.textContent = "Submitting...";
    contactStatus.style.color = "#0c4a6e";

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();

      if (!response.ok || !result.ok) {
        throw new Error(result.error || "Could not submit message.");
      }

      contactStatus.textContent = "Message sent successfully.";
      contactStatus.style.color = "#0f9d58";
      contactForm.reset();
    } catch (error) {
      contactStatus.textContent = error.message || "Something went wrong.";
      contactStatus.style.color = "#d93025";
    }
  });
}

const quoteForm = document.querySelector("#quoteForm");
const quoteStatus = document.querySelector("#quoteStatus");

if (quoteForm && quoteStatus) {
  quoteForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(quoteForm);
    quoteStatus.textContent = "Submitting...";
    quoteStatus.style.color = "#0c4a6e";

    try {
      const response = await fetch("/api/quote", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();

      if (!response.ok || !result.ok) {
        throw new Error(result.error || "Could not submit quote request.");
      }

      quoteStatus.textContent = "Quote request sent successfully.";
      quoteStatus.style.color = "#0f9d58";
      quoteForm.reset();
    } catch (error) {
      quoteStatus.textContent = error.message || "Something went wrong.";
      quoteStatus.style.color = "#d93025";
    }
  });
}
