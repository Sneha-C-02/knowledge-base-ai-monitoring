async function test() {
  const loginRes = await fetch("http://localhost:3000/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", password: "admin123" })
  });
  const loginData = await loginRes.json();
  
  const actsRes = await fetch("http://localhost:3000/api/support/query", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${loginData.token}` 
    },
    body: JSON.stringify({ query: "why is server not connecting to instrument" })
  });
  console.log("Query status:", actsRes.status);
  const actsData = await actsRes.text();
  console.log("Query data:", actsData);
}

test();
