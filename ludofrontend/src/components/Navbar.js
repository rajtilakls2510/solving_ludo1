import React from "react";
import { Link } from "react-router-dom";

const Navbar = () => {
  return (
    <nav className="navbar">
      <div className="nav-center">
        <div className="nav-header">
          <h4>Ludo</h4>
        </div>
        <div className="nav-links-container ">
          <ul className="nav-links ">
            <li>
              <Link to="/vis/gamechoice" className="nav-link">
                Visualizer
              </Link>
            </li>
            <li>
              <Link to="/choose_colour_live_play" className="nav-link">
                Live Play
              </Link>
            </li>
            <li>
              <Link to="/train_stats" className="nav-link">
                Train Stats
              </Link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
