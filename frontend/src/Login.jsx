import { useState } from "react"
import axios from "axios"

function Login({ setIsLoggedIn }) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  const handleLogin = async () => {
    try {
      const response = await axios.post("http://127.0.0.1:8000/api/token/", {
        username: username,
        password: password,
      })

      localStorage.setItem("access", response.data.access)
      localStorage.setItem("refresh", response.data.refresh)

      setIsLoggedIn(true)
    } catch (err) {
      setError("Nom d'utilisateur ou mot de passe incorrect.")
    }
  }

  return (
    <div className="container">
      <h1 className="title">Connexion</h1>

      <div className="search-bar">
        <input
          className="search-input"
          type="text"
          placeholder="Nom d'utilisateur"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <input
          className="search-input"
          type="password"
          placeholder="Mot de passe"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button className="search-button" onClick={handleLogin}>
          Se connecter
        </button>
      </div>

      {error && <p>{error}</p>}
    </div>
  )
}

export default Login