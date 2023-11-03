import React from "react";
import { Route, Routes, BrowserRouter as Router } from "react-router-dom";
import "./normalize.css";
import "./default.css";
import "./main.css";
import Navbar from "./components/Navbar";
import VisualizerFiles from "./components/visualizer/VisualizerFiles";
import VisualizerBoard from "./components/visualizer/VisualizerBoard";
import Board from "./components/Board";
import ColourChooser from "./components/liveplay/ColourChooser";
import LiveBoard from "./components/liveplay/LiveBoard";

function App() {
  return (
    <>
      <Router>
        <Navbar />
        <Routes>
          <Route path="/vis/:run/:file" element={<VisualizerBoard />} />
          <Route path="/vis/gamechoice" element={<VisualizerFiles />} />
          <Route path="/choose_colour_live_play" element={<ColourChooser />} />
          <Route path="/live_play" element={<LiveBoard />} />
          <Route path="*" element={<VisualizerBoard />} />
        </Routes>
      </Router>
    </>
  );
}

export default App;
