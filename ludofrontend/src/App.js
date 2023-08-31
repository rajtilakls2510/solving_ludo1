import React from "react";
import "./normalize.css";
import "./default.css";
import "./main.css";
import Navbar from "./components/Navbar";
import Board from "./components/Board";

function App() {
  return (
    <>
      <Navbar />

      <section className="board-section">
        <Board />
      </section>
    </>
  );
}

export default App;
