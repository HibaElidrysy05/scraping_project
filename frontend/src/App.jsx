import { useState } from "react"
import axios from "axios"
import "./App.css"

function App() {
  const [authMode, setAuthMode] = useState("login")

  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [password2, setPassword2] = useState("")
  const [loginError, setLoginError] = useState("")

  const [isLoggedIn, setIsLoggedIn] = useState(
    !!localStorage.getItem("access")
  )

  const [query, setQuery] = useState("")
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)
  const [showPlatforms, setShowPlatforms] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const [platforms, setPlatforms] = useState(["all"])

  const handleLogin = async () => {
    try {
      const response = await axios.post("http://127.0.0.1:8000/api/token/", {
        username,
        password,
      })

      localStorage.setItem("access", response.data.access)
      localStorage.setItem("refresh", response.data.refresh)

      setIsLoggedIn(true)
      setLoginError("")
    } catch (error) {
      setLoginError("Nom d'utilisateur ou mot de passe incorrect.")
    }
  }

  const handleRegister = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/accounts/api/register/", {
        username,
        email,
        password1: password,
        password2,
      })

      setAuthMode("login")
      setLoginError("Compte créé. Connectez-vous maintenant.")
      setPassword("")
      setPassword2("")
    } catch (error) {
      setLoginError(
        error.response?.data?.error ||
          "Erreur lors de la création du compte."
      )
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("access")
    localStorage.removeItem("refresh")

    setIsLoggedIn(false)
    setProducts([])
    setQuery("")
    setShowProfileMenu(false)
  }

  const handlePlatformChange = (platform) => {
    if (platform === "all") {
      setPlatforms(["all"])
      return
    }

    let updated = platforms.filter((p) => p !== "all")

    if (updated.includes(platform)) {
      updated = updated.filter((p) => p !== platform)
    } else {
      updated.push(platform)
    }

    setPlatforms(updated.length === 0 ? ["all"] : updated)
  }

  const handleSearch = async () => {
    if (!query) return

    setLoading(true)

    try {
      const selectedPlatforms = platforms.includes("all")
        ? "all"
        : platforms.join(",")

      const response = await axios.get(
        `http://127.0.0.1:8000/api/search/?query=${query}&platforms=${selectedPlatforms}`
      )

      setProducts(response.data)
    } catch (error) {
      console.log(error)
    }

    setLoading(false)
  }

  if (!isLoggedIn) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-icon">👤</div>

          <h1 className="login-title">
            {authMode === "login" ? "Connexion" : "Créer un compte"}
          </h1>

          <p className="login-subtitle">
            {authMode === "login"
              ? "Connectez-vous pour accéder au dashboard intelligent"
              : "Créez votre compte pour commencer"}
          </p>

          <input
            type="text"
            placeholder="Nom d'utilisateur"
            className="login-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          {authMode === "register" && (
            <input
              type="email"
              placeholder="Email"
              className="login-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          )}

          <input
            type="password"
            placeholder="Mot de passe"
            className="login-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {authMode === "register" && (
            <input
              type="password"
              placeholder="Confirmer le mot de passe"
              className="login-input"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
            />
          )}

          {authMode === "login" ? (
            <button className="login-button" onClick={handleLogin}>
              Se connecter
            </button>
          ) : (
            <button className="login-button" onClick={handleRegister}>
              Créer mon compte
            </button>
          )}

          {loginError && <p className="login-error">{loginError}</p>}

          <p className="switch-auth">
            {authMode === "login"
              ? "Vous n'avez pas de compte ?"
              : "Vous avez déjà un compte ?"}

            <span
              onClick={() => {
                setAuthMode(authMode === "login" ? "register" : "login")
                setLoginError("")
              }}
            >
              {authMode === "login"
                ? " Créer un compte"
                : " Se connecter"}
            </span>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="profile-container">
        <button
          className="profile-button"
          onClick={() => setShowProfileMenu(!showProfileMenu)}
        >
          👤
        </button>

        {showProfileMenu && (
          <div className="profile-menu">
            <button className="logout-btn" onClick={handleLogout}>
              Déconnexion
            </button>
          </div>
        )}
      </div>

      <h1 className="title">Market Research Dashboard</h1>

      <div className="search-section">
        <div className="search-box">
          <span className="search-icon">🔍</span>

          <input
            type="text"
            placeholder="Cherchez un produit, une marque ou une catégorie"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          <button className="search-button" onClick={handleSearch}>
            Rechercher
          </button>
        </div>

        <div className="filter-container">
          <button
            className="filter-button"
            onClick={() => setShowPlatforms(!showPlatforms)}
          >
            🌐 Tous les sites ⌄
          </button>

          {showPlatforms && (
            <div className="platform-dropdown">
              {[
                "all",
                "jumia",
                "avito",
                "amazon",
                "aliexpress",
                "banggood",
              ].map((platform) => (
                <label key={platform}>
                  <input
                    type="checkbox"
                    checked={platforms.includes(platform)}
                    onChange={() => handlePlatformChange(platform)}
                  />

                  {platform === "all"
                    ? "Tous les sites"
                    : platform.charAt(0).toUpperCase() + platform.slice(1)}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {loading && <p className="loading">Chargement...</p>}

      <div className="products-grid">
        {products.map((product, index) => (
          <div key={index} className="product-card">
            {product.img_link && (
              <img src={product.img_link} alt="" className="product-image" />
            )}

            <div className="product-content">
              <h3>{product.title}</h3>
              <p className="price">{product.price}</p>
              <span className="source-badge">{product.source}</span>

              <a
                href={product.link}
                target="_blank"
                rel="noreferrer"
                className="product-link"
              >
                Voir le produit
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App