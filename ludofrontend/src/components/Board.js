import React, { useState } from "react";
import PContainer from "./PContainer";
import Pos from "./Pos";
import Base from "./Base";

const Board = () => {
  const [boardState, setBoardState] = useState({
    conifg: {
      players: [{ name: "Player 1" }, { name: "Player 2" }],
      player_colour: [
        { "Player 1": ["red", "yellow"] },
        { "Player 2": ["green", "blue"] },
      ],
    },
    pawns: {
      R1: "red",
      R2: "red",
      R3: "red",
      R4: "red",
      G1: "green",
      G2: "green",
      G3: "green",
      G4: "green",
      Y1: "yellow",
      Y2: "yellow",
      Y3: "yellow",
      Y4: "yellow",
      B1: "blue",
      B2: "blue",
      B3: "blue",
      B4: "blue",
    },
    positions: [
      { pawn_id: "R1", pos_id: "RB1", blocked: false },
      { pawn_id: "R2", pos_id: "P23", blocked: true },
      { pawn_id: "R3", pos_id: "P4", blocked: true },
      { pawn_id: "R4", pos_id: "P4", blocked: true },
      { pawn_id: "G1", pos_id: "GB1", blocked: false },
      { pawn_id: "G2", pos_id: "P24", blocked: false },
      { pawn_id: "G3", pos_id: "P35", blocked: false },
      { pawn_id: "G4", pos_id: "P41", blocked: false },
      { pawn_id: "Y1", pos_id: "YB1", blocked: false },
      { pawn_id: "Y2", pos_id: "P28", blocked: false },
      { pawn_id: "Y3", pos_id: "P23", blocked: true },
      { pawn_id: "Y4", pos_id: "YH3", blocked: false },
      { pawn_id: "B1", pos_id: "BB1", blocked: false },
      { pawn_id: "B2", pos_id: "P5", blocked: true },
      { pawn_id: "B3", pos_id: "P5", blocked: true },
      { pawn_id: "B4", pos_id: "BH2", blocked: false },
    ],
    current_player: 0,
    dice_roll: [6, 6, 2],
    blocks: [
      { pawn_ids: ["R3", "R4"], rigid: true },
      { pawn_ids: ["R2", "Y3"], rigid: false },
      { pawn_ids: ["B2", "B3"], rigid: true },
    ],
  });

  return (
    // Layout of the Board
    <div className="board-info-container">
      <div className="board-container">
        <div className="colour-container red-container">
          <Base colour="red" id="R" boardState={boardState} />
        </div>
        <PContainer
          orientation={"vert"}
          colours={["", "", "", "", "", ""]}
          ids={["P12", "P11", "P10", "P9", "P8", "P7"]}
          boardState={boardState}
        ></PContainer>
        <PContainer
          orientation={"vert"}
          colours={["", "green", "green", "green", "green", "green"]}
          ids={["P13", "GH1", "GH2", "GH3", "GH4", "GH5"]}
          boardState={boardState}
        ></PContainer>
        <PContainer
          orientation={"vert"}
          colours={["", "green", "", "", "", ""]}
          ids={["P14", "P15", "P16", "P17", "P18", "P19"]}
          boardState={boardState}
        ></PContainer>
        <div className="colour-container green-container">
          <Base colour="green" id="G" boardState={boardState} />
        </div>
        <PContainer
          orientation={"hor"}
          colours={["", "red", "", "", "", ""]}
          ids={["P1", "P2", "P3", "P4", "P5", "P6"]}
          boardState={boardState}
        ></PContainer>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
        ></Pos>
        <Pos
          container_colour="green"
          classes="middle-winner"
          id="GH6"
          boardState={boardState}
        ></Pos>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
        ></Pos>
        <PContainer
          orientation={"hor"}
          colours={["", "", "", "", "", ""]}
          ids={["P20", "P21", "P22", "P23", "P24", "P25"]}
          boardState={boardState}
        ></PContainer>
        <PContainer
          orientation={"hor"}
          colours={["", "red", "red", "red", "red", "red"]}
          ids={["P52", "RH1", "RH2", "RH3", "RH4", "RH5"]}
          boardState={boardState}
        ></PContainer>
        <Pos
          container_colour="red"
          id="RH6"
          classes="middle-winner"
          boardState={boardState}
        ></Pos>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
        ></Pos>
        <Pos
          container_colour="yellow"
          id="YH6"
          classes="middle-winner"
          boardState={boardState}
        ></Pos>
        <PContainer
          orientation={"hor"}
          colours={["yellow", "yellow", "yellow", "yellow", "yellow", ""]}
          ids={["YH5", "YH4", "YH3", "YH2", "YH1", "P26"]}
          boardState={boardState}
        ></PContainer>
        <PContainer
          orientation={"hor"}
          colours={["", "", "", "", "", ""]}
          ids={["P51", "P50", "P49", "P48", "P47", "P46"]}
          boardState={boardState}
        ></PContainer>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
        ></Pos>
        <Pos
          container_colour="blue"
          id="BH6"
          classes="middle-winner"
          boardState={boardState}
        ></Pos>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
        ></Pos>
        <PContainer
          orientation={"hor"}
          colours={["", "", "", "", "yellow", ""]}
          ids={["P32", "P31", "P30", "P29", "P28", "P27"]}
          boardState={boardState}
        ></PContainer>
        <div className="colour-container blue-container">
          <Base colour="blue" id="B" boardState={boardState} />
        </div>
        <PContainer
          orientation={"vert"}
          colours={["", "", "", "", "blue", ""]}
          ids={["P45", "P44", "P43", "P42", "P41", "P40"]}
          boardState={boardState}
        ></PContainer>
        <PContainer
          orientation={"vert"}
          colours={["blue", "blue", "blue", "blue", "blue", ""]}
          ids={["BH5", "BH4", "BH3", "BH2", "BH1", "P39"]}
          boardState={boardState}
        ></PContainer>
        <PContainer
          orientation={"vert"}
          colours={["", "", "", "", "", ""]}
          ids={["P33", "P34", "P35", "P36", "P37", "P38"]}
          boardState={boardState}
        ></PContainer>
        <div className="colour-container yellow-container">
          <Base colour="yellow" id="Y" boardState={boardState} />
        </div>
      </div>
      <div className="info-container">Info</div>
    </div>
  );
};

export default Board;
