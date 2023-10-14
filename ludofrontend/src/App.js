import React from "react";
import { Route, Routes, BrowserRouter as Router } from "react-router-dom";
import "./normalize.css";
import "./default.css";
import "./main.css";
import Navbar from "./components/Navbar";
import VisualizerFiles from "./components/visualizer/VisualizerFiles";
import VisualizerBoard from "./components/visualizer/VisualizerBoard";
import Board from "./components/Board";

function App() {
  return (
    <>
      <Router>
        <Navbar />
        <Routes>
          <Route path="/vis/:run/:file" element={<VisualizerBoard />} />
          <Route path="/vis/gamechoice" element={<VisualizerFiles />} />
          <Route path="*" element={<Board />} />
        </Routes>
      </Router>
    </>
  );
}

export default App;
