document.addEventListener("DOMContentLoaded", function () {
  const serialInput = document.getElementById("serial_no");
  const loadingOverlay = document.getElementById("loading");
  const enterButton = document.getElementById("enterButton");

  // Ensure elements exist before proceeding
  if (!serialInput) {
    console.error("Serial number input field not found!");
    return;
  }

  const suggestionBox = document.createElement("div");
  suggestionBox.setAttribute("id", "suggestions");
  suggestionBox.style.position = "absolute";
  suggestionBox.style.background = "white";
  suggestionBox.style.border = "1px solid #ccc";
  suggestionBox.style.maxHeight = "250px";
  suggestionBox.style.overflowY = "auto";
  suggestionBox.style.display = "none";
  suggestionBox.style.width = "100%"; 
  suggestionBox.style.top = "40px"; 
  suggestionBox.style.zIndex = "1000"; 
  serialInput.parentNode.appendChild(suggestionBox);
  
  // Pre-fill the serial number if present in the URL query parameter
  const urlParams = new URLSearchParams(window.location.search);
  const serialNo = urlParams.get("serial_no");

  if (serialNo) {
    serialInput.value = serialNo;
    console.log("Serial number found in URL:", serialNo);
    fetchAndProcess(serialNo);
  }

  // Function to fetch serial number suggestions
  function fetchSuggestions(query) {
    if (query.length < 2) {
      suggestionBox.style.display = "none";
      return;
    }

    fetch(`/search_serials?query=${encodeURIComponent(query)}`)
      .then((response) => response.json())
      .then((data) => {
        suggestionBox.innerHTML = "";
        if (data.length === 0) {
          suggestionBox.style.display = "none";
          return;
        }

        data.forEach((serial) => {
          const item = document.createElement("div");
          item.textContent = serial;
          item.style.padding = "8px";
          item.style.cursor = "pointer";

          item.addEventListener("mouseover", function() {
            this.style.backgroundColor = "#e0e0e0"; // Grey color on hover
          });
          item.addEventListener("mouseout", function() {
            this.style.backgroundColor = "white";
          });
          
          item.addEventListener("click", function () {
            serialInput.value = serial;
            suggestionBox.style.display = "none";
            // Do not auto-trigger fetchAndProcess here so selection doesn't immediately redirect
          });
          suggestionBox.appendChild(item);
        });

        suggestionBox.style.display = "block";
      })
      .catch((error) => {
        console.error("Error fetching serials:", error);
      });
  }

  // Function to display an error dialog
  function showErrorDialog(message) {
    // You might already have a dialog element in your HTML.
    // For example, if you have an element with id "errorDialog" and a paragraph with id "errorMessage":
    const errorDialog = document.getElementById("errorDialog");
    const errorMessage = document.getElementById("errorMessage");
    if (errorDialog && errorMessage) {
      errorMessage.innerText = message;
      errorDialog.style.display = "flex";
    } else {
      // Fallback: alert
      alert(message);
    }
  }

  // Function to fetch serial details and handle redirect/pre-fill
  function fetchAndProcess(serial) {
    if (!serial) {
      console.error("Serial number is empty!");
      return;
    }

    if (loadingOverlay) {
      loadingOverlay.style.display = "flex";
    }

    fetch(`/get_serial_details?serial_no=${encodeURIComponent(serial)}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP Error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (data.error) {
          console.error("Error fetching serial details:", data.error);
          if (loadingOverlay) {
            loadingOverlay.style.display = "none";
          }
          showErrorDialog("We were not able to fetch this serial number in our system.\nFor service booking please mail us on: service@electrolabgroup.com");
        } else {
          console.log("Fetched serial details:", data);

          // NEW: Check if customer name is provided
          if (!data.customer || data.customer.trim() === "") {
            if (loadingOverlay) {
              loadingOverlay.style.display = "none";
            }
            showErrorDialog("We were not able to fetch this serial number in our system.\nFor service booking please mail us on: service@electrolabgroup.com");
            return;
          }

          if (window.location.pathname === "/") {
            if (data.maintenance_status === "Under Warranty") {
              console.log("Redirecting to warranty page...");
              window.location.href = `/warranty?serial_no=${encodeURIComponent(serial)}`;
            } else {
              console.log("Redirecting to issue page...");
              window.location.href = `/issue?serial_no=${encodeURIComponent(serial)}`;
            }
          } else {
            // On Issue or Warranty pages, pre-fill additional fields
            serialInput.value = serial;

            if (document.getElementById("item_name")) {
              document.getElementById("item_name").value = data.item_name || "";
            }
            if (document.getElementById("customer")) {
              document.getElementById("customer").value = data.customer || "";
            }
            if (document.getElementById("customer_address")) {
              document.getElementById("customer_address").value = data.customer_address || "";
            }
            if (document.getElementById("zonal_manager")) {
              document.getElementById("zonal_manager").value = data.zonal_manager || "";
            }
            if (document.getElementById("customer_name")) {
              document.getElementById("customer_name").value = data.customer || "";
            }
            if (document.getElementById("amc_type")) {
              document.getElementById("amc_type").value = data.amc_type || "Out Of Warranty";
            }

            if (loadingOverlay) {
              loadingOverlay.style.display = "none";
            }
          }
        }
      })
      .catch((err) => {
        console.error("Fetch error:", err);
        if (loadingOverlay) {
          loadingOverlay.style.display = "none";
        }
      });
  }

  // Add click event listener to the search button
  if (enterButton) {
    enterButton.addEventListener("click", function() {
      const query = serialInput.value.trim();
      if (query) {
        fetchAndProcess(query);
      }
    });
  }

  // Attach event listener for serial number input
  serialInput.addEventListener("input", function () {
    const query = serialInput.value.trim();
    fetchSuggestions(query);
  });

  serialInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      const query = serialInput.value.trim();
      if (query) {
        fetchAndProcess(query); // Process on Enter key as well
      }
      serialInput.blur();
      suggestionBox.style.display = "none";
    }
  });

  serialInput.addEventListener("blur", function () {
    setTimeout(() => {
      suggestionBox.style.display = "none";
    }, 200);
  });

  // If a serial number is provided in the URL, fetch details
  if (serialNo) {
    setTimeout(() => {
      fetchAndProcess(serialNo);
    }, 500);
  }
});
