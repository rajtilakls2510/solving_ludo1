import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Api from "../../Api";

const ColourChooser = () => {
  const [loader, setLoader] = useState(false);
  const navigate = useNavigate();
  useEffect(() => {
    Api.checkRunningGame()
      .then((res) => {
        if (res.data.running) {
          navigate("/live_play");
        }
      })
      .catch((err) => {
        console.log(err);
      });
  }, []);

  const create_new_game = (colours) => {
    setLoader(true);
    if (colours === "ry")
      Api.createNewGame([
        { mode: "AI", colours: ["green", "blue"] },
        { mode: "Human", colours: ["red", "yellow"] },
      ])
        .then((res) => {
          if (res.status === 200) {
            navigate("/live_play");
          }
        })
        .catch((err) => {
          console.log(err);
        })
        .finally((e) => {
          setLoader(false);
        });
    else
      Api.createNewGame([
        { mode: "AI", colours: ["red", "yellow"] },
        { mode: "Human", colours: ["green", "blue"] },
      ])
        .then((res) => {
          if (res.status === 200) {
            navigate("/live_play");
          }
        })
        .catch((err) => {
          console.log(err);
        })
        .finally((e) => {
          setLoader(false);
        });
  };

  return (
    <section className="board-section">
      <div className="visualizer-file-container">
        <div className="card run-container">
          <h5>Choose Colour for Doubles:</h5>

          <div className="live-double-colour-container">
            <div
              className="player-container colour-combination"
              onClick={() => create_new_game("ry")}
            >
              <button className={`btn pawn btn-red`}></button>
              <button className={`btn pawn btn-yellow`}></button>
              <span>Combination 1</span>
            </div>
            <div
              className="player-container colour-combination"
              onClick={() => create_new_game("gb")}
            >
              <button className={`btn pawn btn-green`}></button>
              <button className={`btn pawn btn-blue`}></button>
              <span>Combination 2</span>
            </div>
          </div>
          {loader ? <div className="loader"></div> : ""}
        </div>
        <div className="card run-container">
          <h5>Choose Game configuration for Singles:</h5>
          <span>NOT IMPLEMENTED YET</span>
        </div>
      </div>
    </section>
  );
};

export default ColourChooser;
