
import { useState } from "react";
import {
  ArrowDownUp,
  ArrowRight,
  Bell,
  CalendarDays,
  Check,
  ChevronDown,
  CircleHelp,
  Compass,
  Globe2,
  Plane,
  Search,
  ShieldCheck,
  Sparkles,
  Ticket,
  Users,
} from "lucide-react";
type FlightSearch = {
  origin: string;
  destination: string;
  departureDate: string;
  returnDate: string;
  tripType: "one-way" | "round-trip";
  passengers: number;
  cabin: string;
};

function App() {
  const [activeNav, setActiveNav] = useState("Flights");
  const [search, setSearch] = useState<FlightSearch>({
    origin: "RGN",
    destination: "BKK",
    departureDate: "2026-11-15",
    returnDate: "",
    tripType: "one-way",
    passengers: 1,
    cabin: "Economy",
  });
  const [notice, setNotice] = useState("");
  const [searching, setSearching] = useState(false);

  function update<K extends keyof FlightSearch>(
    key: K,
    value: FlightSearch[K],
  ) {
    setSearch((previous) => ({ ...previous, [key]: value }));
  }

  function swapAirports() {
    setSearch((previous) => ({
      ...previous,
      origin: previous.destination,
      destination: previous.origin,
    }));
  }

  async function searchFlights(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");

    if (!search.origin.trim() || !search.destination.trim()) {
      setNotice("Please enter both departure and destination airports.");
      return;
    }

    if (search.origin.trim().toUpperCase() === search.destination.trim().toUpperCase()) {
      setNotice("Departure and destination airports must be different.");
      return;
    }

    if (!search.departureDate) {
      setNotice("Please select your departure date.");
      return;
    }

    setSearching(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8018/api/v1/flights/search",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            origin: search.origin.trim().toUpperCase(),
            destination: search.destination.trim().toUpperCase(),
            departure_date: search.departureDate,
            return_date:
              search.tripType === "round-trip" ? search.returnDate || null : null,
            passengers: search.passengers,
            cabin_class: search.cabin.toLowerCase(),
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Flight search failed.");
      }

      sessionStorage.setItem("apexiveai_flight_search", JSON.stringify(search));
      sessionStorage.setItem("apexiveai_flight_results", JSON.stringify(data));

      setNotice(
        "Search completed. Results received from the current backend. Demo offers may be simulated, not live airline inventory.",
      );
      window.location.hash = "results";
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to connect to the API.";

      setNotice(
        `${message} Check that the backend is running at http://127.0.0.1:8018.`,
      );
    } finally {
      setSearching(false);
    }
  }

  const navItems = [
    { label: "Flights", icon: Plane },
    { label: "My bookings", icon: Ticket },
    { label: "Travelers", icon: Users },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="ApexiveAI home">
          <span className="brand-symbol">
            <Plane size={19} strokeWidth={2.2} />
          </span>
          <span className="brand-copy">
            <strong>apexive<span>ai</span></strong>
            <small>TRAVEL SYSTEMS</small>
          </span>
        </a>

        <div className="workspace-label">WORKSPACE</div>

        <nav className="main-nav" aria-label="Main navigation">
          {navItems.map(({ label, icon: Icon }) => (
            <button
              className={`nav-item ${activeNav === label ? "active" : ""}`}
              key={label}
              onClick={() => {
                setActiveNav(label);
                if (label !== "Flights") {
                  setNotice(`${label} workspace is not implemented yet.`);
                } else {
                  setNotice("");
                }
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === "Flights" && <span className="nav-dot" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="support-card">
            <span className="support-icon"><CircleHelp size={18} /></span>
            <strong>Need a hand?</strong>
            <p>Your travel workspace, all in one place.</p>
            <button onClick={() => setNotice("Support center is coming soon.")}>
              Get support <ArrowRight size={14} />
            </button>
          </div>
          <div className="profile">
            <div className="avatar">A</div>
            <div className="profile-info">
              <strong>ApexiveAI</strong>
              <span>Travel workspace</span>
            </div>
            <button
              className="icon-button profile-menu"
              aria-label="Profile menu"
              onClick={() => setNotice("Account settings are coming soon.")}
            >
              <ChevronDown size={16} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{activeNav}</strong>
          </div>
          <div className="topbar-actions">
            <span className="environment"><span /> LOCAL ENVIRONMENT</span>
            <button
              className="icon-button notification-button"
              aria-label="Notifications"
              onClick={() => setNotice("You’re all caught up.")}
            >
              <Bell size={18} />
            </button>
            <button
              className="help-link"
              onClick={() => setNotice("Help center is coming soon.")}
            >
              <CircleHelp size={17} /> Help
            </button>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><Sparkles size={14} /> YOUR NEXT JOURNEY STARTS HERE</div>
              <h1>Travel, without<br className="mobile-break" /> the noise.</h1>
              <p className="page-subtitle">
                A smarter way to discover flights and manage every journey.
              </p>
            </div>
            <div className="welcome-decoration" aria-hidden="true">
              <div className="orbit orbit-one" />
              <div className="orbit orbit-two" />
              <div className="orbit-plane"><Plane size={30} /></div>
              <span className="star star-one">✳</span>
              <span className="star star-two">✦</span>
            </div>
          </section>

          <section className="search-panel">
            <div className="panel-top">
              <div className="panel-heading">
                <div className="heading-icon"><Compass size={19} /></div>
                <div>
                  <h2>Find your flight</h2>
                  <p>Where would you like to go?</p>
                </div>
              </div>
              <div className="trip-toggle">
                <button
                  className={search.tripType === "round-trip" ? "selected" : ""}
                  onClick={() => update("tripType", "round-trip")}
                  type="button"
                >
                  Round trip
                </button>
                <button
                  className={search.tripType === "one-way" ? "selected" : ""}
                  onClick={() => update("tripType", "one-way")}
                  type="button"
                >
                  One way
                </button>
              </div>
            </div>

            <form onSubmit={searchFlights}>
              <div className="flight-fields">
                <label className="field airport-field">
                  <span className="field-label">FROM</span>
                  <span className="field-value">
                    <input
                      aria-label="Departure airport code"
                      maxLength={3}
                      value={search.origin}
                      onChange={(event) =>
                        update("origin", event.target.value.toUpperCase())
                      }
                      placeholder="RGN"
                    />
                    <span className="airport-caption">Departure airport</span>
                  </span>
                </label>

                <button
                  className="swap-button"
                  type="button"
                  onClick={swapAirports}
                  aria-label="Swap departure and destination"
                  title="Swap airports"
                >
                  <ArrowDownUp size={17} />
                </button>

                <label className="field airport-field">
                  <span className="field-label">TO</span>
                  <span className="field-value">
                    <input
                      aria-label="Destination airport code"
                      maxLength={3}
                      value={search.destination}
                      onChange={(event) =>
                        update("destination", event.target.value.toUpperCase())
                      }
                      placeholder="BKK"
                    />
                    <span className="airport-caption">Destination airport</span>
                  </span>
                </label>

                <label className="field date-field">
                  <span className="field-label"><CalendarDays size={13} /> DEPARTURE</span>
                  <input
                    aria-label="Departure date"
                    type="date"
                    value={search.departureDate}
                    onChange={(event) => update("departureDate", event.target.value)}
                    required
                  />
                </label>

                {search.tripType === "round-trip" && (
                  <label className="field date-field">
                    <span className="field-label"><CalendarDays size={13} /> RETURN</span>
                    <input
                      aria-label="Return date"
                      type="date"
                      min={search.departureDate}
                      value={search.returnDate}
                      onChange={(event) => update("returnDate", event.target.value)}
                      required
                    />
                  </label>
                )}

                <label className="field passengers-field">
                  <span className="field-label"><Users size={13} /> TRAVELERS</span>
                  <select
                    aria-label="Number of passengers"
                    value={search.passengers}
                    onChange={(event) => update("passengers", Number(event.target.value))}
                  >
                    <option value={1}>1 traveler</option>
                    <option value={2}>2 travelers</option>
                    <option value={3}>3 travelers</option>
                    <option value={4}>4 travelers</option>
                    <option value={5}>5 travelers</option>
                    <option value={6}>6 travelers</option>
                    <option value={7}>7 travelers</option>
                    <option value={8}>8 travelers</option>
                    <option value={9}>9 travelers</option>
                  </select>
                </label>

                <label className="field cabin-field">
                  <span className="field-label">CABIN CLASS</span>
                  <select
                    aria-label="Cabin class"
                    value={search.cabin}
                    onChange={(event) => update("cabin", event.target.value)}
                  >
                    <option>Economy</option>
                    <option>Premium Economy</option>
                    <option>Business</option>
                    <option>First</option>
                  </select>
                </label>
              </div>

              <div className="search-bottom">
                <span className="search-hint">
                  <ShieldCheck size={15} /> Search options securely
                </span>
                <button className="search-button" type="submit" disabled={searching}>
                  <Search size={17} />
                  {searching ? "Searching..." : "Search flights"}
                  {!searching && <ArrowRight size={16} />}
                </button>
              </div>
            </form>
          </section>

          {notice && (
            <div className="notice" role="status">
              <span className="notice-check"><Check size={15} /></span>
              <p>{notice}</p>
              <button aria-label="Dismiss message" onClick={() => setNotice("")}>×</button>
            </div>
          )}

          <section className="quick-stats">
            <div className="stat-card">
              <div className="stat-icon purple"><Globe2 size={19} /></div>
              <div className="stat-copy">
                <span>DESTINATIONS</span>
                <strong>Worldwide</strong>
                <small>Provider coverage to come</small>
              </div>
              <ArrowRight size={16} className="stat-arrow" />
            </div>
            <div className="stat-card">
              <div className="stat-icon blue"><Ticket size={19} /></div>
              <div className="stat-copy">
                <span>BOOKING MANAGEMENT</span>
                <strong>One workspace</strong>
                <small>Keep trip details together</small>
              </div>
              <ArrowRight size={16} className="stat-arrow" />
            </div>
            <div className="stat-card">
              <div className="stat-icon green"><ShieldCheck size={19} /></div>
              <div className="stat-copy">
                <span>BOOKING STATUS</span>
                <strong>Track every step</strong>
                <small>Ticket issuance depends on provider</small>
              </div>
              <ArrowRight size={16} className="stat-arrow" />
            </div>
          </section>

          <section className="bottom-section" id="results">
            <div className="section-title-row">
              <div>
                <h2>Built for better journeys.</h2>
                <p>Everything you need, without the clutter.</p>
              </div>
              <span className="coming-soon">WORKSPACE PREVIEW</span>
            </div>

            <div className="feature-grid">
              <article className="feature-card">
                <div className="feature-top">
                  <span className="feature-icon"><Compass size={20} /></span>
                  <span className="feature-number">01</span>
                </div>
                <h3>Discover</h3>
                <p>Search available offers through connected travel providers as integrations become available.</p>
                <span className="feature-status"><span /> Search interface ready</span>
              </article>
              <article className="feature-card">
                <div className="feature-top">
                  <span className="feature-icon"><Ticket size={20} /></span>
                  <span className="feature-number">02</span>
                </div>
                <h3>Manage</h3>
                <p>Keep traveler details, booking references, and status updates organized in one place.</p>
                <span className="feature-status pending"><span /> Booking UI in progress</span>
              </article>
              <article className="feature-card">
                <div className="feature-top">
                  <span className="feature-icon"><Sparkles size={20} /></span>
                  <span className="feature-number">03</span>
                </div>
                <h3>Automate</h3>
                <p>Prepare provider-independent workflows for booking, payment verification, and ticketing.</p>
                <span className="feature-status pending"><span /> Integrations pending</span>
              </article>
            </div>
          </section>

          <footer className="footer">
            <div className="footer-brand">
              <span className="footer-mark"><Plane size={13} /></span>
              <strong>APEXIVEAI</strong>
              <span>© 2026</span>
            </div>
            <span className="footer-note"><span /> Development environment · Demo data may be simulated</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
