(async function logUserDetails() {
    try {
        const response = await fetch("/api/handler", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        const result = await response.json();
        console.log(result);
    } catch (error) {
        console.error("Error logging data:", error);
    }
})();
