import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import PContainer from "../PContainer";
import {
  FaFastForward,
  FaFastBackward,
  FaForward,
  FaBackward,
  FaStepForward,
  FaStepBackward,
} from "react-icons/fa";
import { IconContext } from "react-icons";
import Pos from "../Pos";
import Base from "../Base";
import Api from "../../Api";
const VisualizerBoard = () => {
  const [info, setInfo] = useState({
    config: {
      players: [
        { name: "Player 1", colours: ["red", "yellow"] },
        { name: "Player 2", colours: ["green", "blue"] },
      ],
      player_colour: [
        { "Player 1": ["red", "yellow"] },
        { "Player 2": ["green", "blue"] },
      ],
    },
    game: [
      {
        game_state: {
          pawns: {
            R1: { colour: "red", blocked: false },
            R2: { colour: "red", blocked: true },
            R3: { colour: "red", blocked: true },
            R4: { colour: "red", blocked: true },
            G1: { colour: "green", blocked: false },
            G2: { colour: "green", blocked: false },
            G3: { colour: "green", blocked: false },
            G4: { colour: "green", blocked: false },
            Y1: { colour: "yellow", blocked: false },
            Y2: { colour: "yellow", blocked: false },
            Y3: { colour: "yellow", blocked: true },
            Y4: { colour: "yellow", blocked: false },
            B1: { colour: "blue", blocked: false },
            B2: { colour: "blue", blocked: true },
            B3: { colour: "blue", blocked: true },
            B4: { colour: "blue", blocked: false },
          },
          positions: [
            { pawn_id: "R1", pos_id: "RB1" },
            { pawn_id: "R2", pos_id: "P23" },
            { pawn_id: "R3", pos_id: "P4" },
            { pawn_id: "R4", pos_id: "P4" },
            { pawn_id: "G1", pos_id: "GB1" },
            { pawn_id: "G2", pos_id: "P24" },
            { pawn_id: "G3", pos_id: "P35" },
            { pawn_id: "G4", pos_id: "P41" },
            { pawn_id: "Y1", pos_id: "YB1" },
            { pawn_id: "Y2", pos_id: "P28" },
            { pawn_id: "Y3", pos_id: "P23" },
            { pawn_id: "Y4", pos_id: "YH3" },
            { pawn_id: "B1", pos_id: "BB1" },
            { pawn_id: "B2", pos_id: "P5" },
            { pawn_id: "B3", pos_id: "P5" },
            { pawn_id: "B4", pos_id: "BH2" },
          ],
          last_move_id: 0,
          current_player: 0,
          dice_roll: [6, 6, 2],
          blocks: [
            { pawn_ids: ["R3", "R4"], rigid: true },
            { pawn_ids: ["R2", "Y3"], rigid: false },
            { pawn_ids: ["B2", "B3"], rigid: true },
          ],
          game_over: false,
          num_more_moves: 0,
        },
        move_id: 0,
        move: [["B4", "P16", "P18"]],
      },
    ],
    player_won: 3, // 1-indexed
  });
  const { run, file } = useParams();
  const [boardState, setBoardState] = useState({
    game_state: {
      pawns: {
        R1: { colour: "red", blocked: false },
        R2: { colour: "red", blocked: true },
        R3: { colour: "red", blocked: true },
        R4: { colour: "red", blocked: true },
        G1: { colour: "green", blocked: false },
        G2: { colour: "green", blocked: false },
        G3: { colour: "green", blocked: false },
        G4: { colour: "green", blocked: false },
        Y1: { colour: "yellow", blocked: false },
        Y2: { colour: "yellow", blocked: false },
        Y3: { colour: "yellow", blocked: true },
        Y4: { colour: "yellow", blocked: false },
        B1: { colour: "blue", blocked: false },
        B2: { colour: "blue", blocked: true },
        B3: { colour: "blue", blocked: true },
        B4: { colour: "blue", blocked: false },
      },
      positions: [
        { pawn_id: "R1", pos_id: "RB1" },
        { pawn_id: "R2", pos_id: "P23" },
        { pawn_id: "R3", pos_id: "P4" },
        { pawn_id: "R4", pos_id: "P4" },
        { pawn_id: "G1", pos_id: "GB1" },
        { pawn_id: "G2", pos_id: "P24" },
        { pawn_id: "G3", pos_id: "P35" },
        { pawn_id: "G4", pos_id: "P41" },
        { pawn_id: "Y1", pos_id: "YB1" },
        { pawn_id: "Y2", pos_id: "P28" },
        { pawn_id: "Y3", pos_id: "P23" },
        { pawn_id: "Y4", pos_id: "YH3" },
        { pawn_id: "B1", pos_id: "BB1" },
        { pawn_id: "B2", pos_id: "P5" },
        { pawn_id: "B3", pos_id: "P5" },
        { pawn_id: "B4", pos_id: "BH2" },
      ],
      last_move_id: 0,
      current_player: 0,
      dice_roll: [6, 6, 2],
      blocks: [
        { pawn_ids: ["R3", "R4"], rigid: true },
        { pawn_ids: ["R2", "Y3"], rigid: false },
        { pawn_ids: ["B2", "B3"], rigid: true },
      ],
      game_over: false,
      num_more_moves: 0,
      selected_pawns: [],
      available_pos: [],
    },
    move_id: 0,
    move: [["B4", "P16", "P18"]],
  });

  useEffect(() => {
    Api.getLogFile(run, file)
      .then((res) => {
        setInfo(res.data);
        setBoardState({
          game_state: {
            ...res.data.game[0].game_state,
            selected_pawns: [],
            available_pos: [],
          },
          move_id: res.data.game[0].move_id,
          move: res.data.game[0].move,
        });
      })
      .catch((err) => {
        console.log(err);
      });
  }, []);

  const handleStep = (steps) => {
    let new_move_id = boardState.move_id + steps;
    if (new_move_id < 0) new_move_id = 0;
    else if (new_move_id >= info.game.length)
      new_move_id = info.game.length - 1;
    setBoardState({
      game_state: {
        ...info.game[new_move_id].game_state,
        selected_pawns: [],
        available_pos: [],
      },
      move_id: info.game[new_move_id].move_id,
      move: info.game[new_move_id].move,
    });
  };

  return (
    <section className="board-section">
      <div className="board-info-container">
        <div className="board-container">
          <div className="colour-container red-container">
            <Base
              colour="red"
              id="R"
              boardState={boardState.game_state}
              handlePawnClick={() => {}}
              handlePosClick={() => {}}
            />
          </div>
          <PContainer
            orientation={"vert"}
            colours={["", "", "", "", "", ""]}
            ids={["P12", "P11", "P10", "P9", "P8", "P7"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <PContainer
            orientation={"vert"}
            colours={["", "green", "green", "green", "green", "green"]}
            ids={["P13", "GH1", "GH2", "GH3", "GH4", "GH5"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <PContainer
            orientation={"vert"}
            colours={["", "green", "", "", "", ""]}
            ids={["P14", "P15", "P16", "P17", "P18", "P19"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <div className="colour-container green-container">
            <Base
              colour="green"
              id="G"
              boardState={boardState.game_state}
              handlePawnClick={() => {}}
              handlePosClick={() => {}}
            />
          </div>
          <PContainer
            orientation={"hor"}
            colours={["", "red", "", "", "", ""]}
            ids={["P1", "P2", "P3", "P4", "P5", "P6"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <Pos
            container_colour="disabled"
            id=""
            classes="middle-winner"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <Pos
            container_colour="green"
            classes="middle-winner"
            id="GH6"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <Pos
            container_colour="disabled"
            id=""
            classes="middle-winner"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <PContainer
            orientation={"hor"}
            colours={["", "", "", "", "", ""]}
            ids={["P20", "P21", "P22", "P23", "P24", "P25"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <PContainer
            orientation={"hor"}
            colours={["", "red", "red", "red", "red", "red"]}
            ids={["P52", "RH1", "RH2", "RH3", "RH4", "RH5"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <Pos
            container_colour="red"
            id="RH6"
            classes="middle-winner"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <Pos
            container_colour="disabled"
            id=""
            classes="middle-winner"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <Pos
            container_colour="yellow"
            id="YH6"
            classes="middle-winner"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <PContainer
            orientation={"hor"}
            colours={["yellow", "yellow", "yellow", "yellow", "yellow", ""]}
            ids={["YH5", "YH4", "YH3", "YH2", "YH1", "P26"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <PContainer
            orientation={"hor"}
            colours={["", "", "", "", "", ""]}
            ids={["P51", "P50", "P49", "P48", "P47", "P46"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <Pos
            container_colour="disabled"
            id=""
            classes="middle-winner"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <Pos
            container_colour="blue"
            id="BH6"
            classes="middle-winner"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <Pos
            container_colour="disabled"
            id=""
            classes="middle-winner"
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></Pos>
          <PContainer
            orientation={"hor"}
            colours={["", "", "", "", "yellow", ""]}
            ids={["P32", "P31", "P30", "P29", "P28", "P27"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <div className="colour-container blue-container">
            <Base
              colour="blue"
              id="B"
              boardState={boardState.game_state}
              handlePawnClick={() => {}}
              handlePosClick={() => {}}
            />
          </div>
          <PContainer
            orientation={"vert"}
            colours={["", "", "", "", "blue", ""]}
            ids={["P45", "P44", "P43", "P42", "P41", "P40"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <PContainer
            orientation={"vert"}
            colours={["blue", "blue", "blue", "blue", "blue", ""]}
            ids={["BH5", "BH4", "BH3", "BH2", "BH1", "P39"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <PContainer
            orientation={"vert"}
            colours={["", "", "", "", "", ""]}
            ids={["P33", "P34", "P35", "P36", "P37", "P38"]}
            boardState={boardState.game_state}
            handlePawnClick={() => {}}
            handlePosClick={() => {}}
          ></PContainer>
          <div className="colour-container yellow-container">
            <Base
              colour="yellow"
              id="Y"
              boardState={boardState.game_state}
              handlePawnClick={() => {}}
              handlePosClick={() => {}}
            />
          </div>
        </div>
        <div className="info-container">
          <div className="step-container">
            <IconContext.Provider value={{ className: "step-icons", size: 30 }}>
              <>
                <FaFastBackward onClick={() => handleStep(-info.game.length)} />
                <FaBackward onClick={() => handleStep(-10)} />
                <FaStepBackward onClick={() => handleStep(-1)} />
                <span>Move: {boardState.move_id}</span>
                <FaStepForward onClick={() => handleStep(1)} />
                <FaForward onClick={() => handleStep(10)} />
                <FaFastForward onClick={() => handleStep(info.game.length)} />
              </>
            </IconContext.Provider>
          </div>
          <div className="players-container">
            {info.config.players.map((player, index) => {
              return (
                <div
                  key={player.name}
                  className={`player-container ${
                    index === boardState.game_state.current_player
                      ? "current-player"
                      : ""
                  } ${
                    boardState.move_id + 1 === info.game.length &&
                    index + 1 === info.player_won
                      ? "winner-player"
                      : ""
                  }`}
                >
                  {player.colours.map((colour) => {
                    return (
                      <button className={`btn pawn btn-${colour}`}></button>
                    );
                  })}
                  <span>{player.name}</span>
                </div>
              );
            })}
          </div>
          <div className="roll-num-container">
            <div>Roll: {JSON.stringify(boardState.game_state.dice_roll)}</div>
            <div>No. of Moves Left: {boardState.game_state.num_more_moves}</div>
          </div>
          <div className="move-taken-container">
            <span> Move Taken: </span>
            <span> {JSON.stringify(boardState.move)}</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default VisualizerBoard;
