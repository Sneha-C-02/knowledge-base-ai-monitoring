async function test() {
  const loginRes = await fetch("http://localhost:3000/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", password: "admin123" })
  });
  const loginData = await loginRes.json();
  
  const actsRes = await fetch("http://localhost:3000/api/system/stats", {
    headers: { "Authorization": `Bearer ${loginData.token}` }
  });
  console.log("Stats status:", actsRes.status);
  const actsData = await actsRes.json();
  console.log("Stats data:", JSON.stringify(actsData));
}

test();
