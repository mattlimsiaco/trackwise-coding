const recordSelect = document.getElementById("record-select");
const pageTitle = document.getElementById("page-title");
const box = document.getElementById("prediction-box");

recordSelect.addEventListener("change", () => {
  if (recordSelect.value) {
    if (!pageTitle.classList.contains("animate-title")) {
      pageTitle.classList.add("animate-title");
    }

    recordSelect.classList.add("fade-out");

    box.classList.remove("hidden");
    box.classList.add("fade-in");
  }
});

const predictBtn = document.getElementById("predict-button");
const resultDiv = document.getElementById("prediction-result");
const spinner = document.querySelector(".spinner");

predictBtn.addEventListener("click", () => {
  const eventDesc = document.getElementById("event-description").value.trim();
  const productId = document.getElementById("product-id").value.trim();

  resultDiv.classList.add("hidden");

  if (!eventDesc || !productId) {
    resultDiv.textContent = "Please fill in both Event Description and Product Identification.";
    resultDiv.classList.remove("hidden");
    return;
  }

  spinner.style.display = "block";

  fetch("/predict", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      event_description: eventDesc,
      product_id: productId
    })
  })
    .then(response => {
      spinner.style.display = "none";
      if (!response.ok) {
        throw new Error("Prediction failed");
      }
      return response.json();
    })
    .then(data => {
      const code = data.code || "Unknown";
      const term = data.term || "Unknown Term";
      resultDiv.textContent = `Device Code ${code}: ${term}`;

      resultDiv.classList.remove("hidden");
    })
    .catch(error => {
      resultDiv.textContent = "An error occurred while predicting. Please try again.";
      resultDiv.classList.remove("hidden");
      console.error("Error:", error);
    });
});


