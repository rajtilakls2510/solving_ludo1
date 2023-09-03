import React, { useState, useEffect } from "react";
import PContainer from "./PContainer";
import Pos from "./Pos";
import Base from "./Base";
import Api from "../Api";

const Board = () => {
  const [availableMoves, setAvailableMoves] = useState([]);
  // const [sendMove, setSendMove] = useState(false);
  const [boardState, setBoardState] = useState({
    config: {
      players: [{ name: "Player 1" }, { name: "Player 2" }],
      player_colour: [
        { "Player 1": ["red", "yellow"] },
        { "Player 2": ["green", "blue"] },
      ],
    },
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
    moves: [],
    current_move: [],
    selected_pawns: [],
    available_pos: [],
  });

  const applyBoardState = (data) => {
    setBoardState({
      ...data,
      current_move: [],
      selected_pawns: [],
      available_pos: [],
    });
    if (JSON.stringify(data.moves) === JSON.stringify([])) {
      setAvailableMoves([[]]);
    } else {
      setAvailableMoves([...data.moves]);
    }
  };

  useEffect(() => {
    Api.getState()
      .then((res) => {
        applyBoardState(res.data);
      })
      .catch((error) => {
        console.log(error);
        console.log("State fetch error");
      });
  }, []);

  const checkContainsInArrayUsingPos = (moves, move) => {
    if (!Array.isArray(move[0])) {
      for (let i = 0; i < moves.length; i++) {
        if (
          !Array.isArray(moves[i][0]) &&
          moves[i][0] === move[0] &&
          moves[i][2] === move[1]
        )
          return true;
      }
    } else {
      for (let i = 0; i < moves.length; i++) {
        if (
          Array.isArray(moves[i][0]) &&
          moves[i][0].every((elem) => move[0].includes(elem)) &&
          moves[i][2] === move[1]
        )
          return true;
      }
    }
    return false;
  };

  const checkSame = (arr1, arr2) => {
    let same1 = true;
    for (let i = 0; i < arr1.length; i++) {
      let same2 = false;
      for (let j = 0; j < arr2.length; j++) {
        let same3 = true;
        for (let k = 0; k < arr1[i].length; k++) {
          if (Array.isArray(arr1[i][k]) && Array.isArray(arr2[j][k]))
            same3 &=
              JSON.stringify(arr1[i][k].sort()) ===
              JSON.stringify(arr2[j][k].sort());
          else if (!Array.isArray(arr1[i][k]) && !Array.isArray(arr2[j][k]))
            same3 &= arr1[i][k] === arr2[j][k];
          else same3 &= false;
        }
        same2 |= same3;
      }
      same1 &= same2;
    }
    return same1;
  };

  useEffect(() => {
    if (
      JSON.stringify(availableMoves) !== JSON.stringify([[]]) &&
      JSON.stringify(availableMoves) !== JSON.stringify([])
    ) {
      console.log("nd", availableMoves);
      let move_completed = true;
      let initial = availableMoves[0];
      for (let i = 1; i < availableMoves.length; i++)
        move_completed &= checkSame(initial, availableMoves[i]);

      if (move_completed) {
        Api.postMove({
          move: availableMoves[0],
          move_id: boardState.last_move_id + 1,
        })
          .then((res) => {
            applyBoardState(res.data);
          })
          .catch((error) => {
            console.log("State fetch error");
          });
      }
    } else if (JSON.stringify(availableMoves) === JSON.stringify([[]])) {
      console.log("no valid move found, skipping turn");
      console.log("d", availableMoves);
      Api.postMove({ move: [[]], move_id: boardState.last_move_id + 1 })
        .then((res) => {
          applyBoardState(res.data);
        })
        .catch((error) => {
          console.log("State fetch error");
        });
    }
  }, [availableMoves]);

  // useEffect(() => {
  //   let move_completed = true;
  //   if (
  //     JSON.stringify(availableMoves) !== JSON.stringify([[]]) &&
  //     JSON.stringify(availableMoves) !== JSON.stringify([])
  //   ) {

  //     setSendMove(move_completed);
  //   }
  // }, [availableMoves]);

  useEffect(() => {
    let moves1 = [...availableMoves];
    for (let i = 0; i < boardState.current_move.length; i++) {
      moves1 = moves1.filter((elem) =>
        checkContainsInArrayUsingPos(elem, boardState.current_move[i])
      );
    }
    setAvailableMoves(moves1);
  }, [boardState.current_move]);

  useEffect(() => {
    let available_pos = [];
    if (boardState.selected_pawns.length === 1) {
      for (let i = 0; i < availableMoves.length; i++) {
        for (let j = 0; j < availableMoves[i].length; j++) {
          if (
            !Array.isArray(availableMoves[i][j][0]) &&
            availableMoves[i][j][0] === boardState.selected_pawns[0] &&
            !available_pos.includes(availableMoves[i][j][2])
          )
            available_pos.push(availableMoves[i][j][2]);
        }
      }
    } else if (boardState.selected_pawns.length > 1) {
      for (let i = 0; i < availableMoves.length; i++) {
        for (let j = 0; j < availableMoves[i].length; j++) {
          if (
            Array.isArray(availableMoves[i][j][0]) &&
            availableMoves[i][j][0].every((elem) =>
              boardState.selected_pawns.includes(elem)
            ) &&
            !available_pos.includes(availableMoves[i][j][2])
          )
            available_pos.push(availableMoves[i][j][2]);
        }
      }
    }
    setBoardState({ ...boardState, available_pos: available_pos });
  }, [boardState.selected_pawns]);

  const handlePawnClick = (pawn_id) => {
    let selected_pawns = boardState.selected_pawns;
    if (boardState.selected_pawns.includes(pawn_id)) {
      // If pawn is already selected, remove it from selected list and any other rigid block pawns
      selected_pawns = selected_pawns.filter((elem) => elem !== pawn_id);
      let block = boardState.blocks.filter((elem) =>
        elem.pawn_ids.includes(pawn_id)
      );

      if (block.length === 1 && block[0].rigid)
        selected_pawns = selected_pawns.filter(
          (elem) => !block[0].pawn_ids.includes(elem)
        );
    } else {
      // If pawn is not selected, add it to selected list and any other rigid block pawns
      let block = boardState.blocks.filter((elem) =>
        elem.pawn_ids.includes(pawn_id)
      );

      if (block.length === 1 && block[0].rigid)
        selected_pawns = [...selected_pawns, ...block[0].pawn_ids];
      else selected_pawns = [...selected_pawns, pawn_id];
    }
    setBoardState({
      ...boardState,
      selected_pawns: selected_pawns,
    });
  };
  const handlePosClick = (pos_id) => {
    let selected_pawns = boardState.selected_pawns;
    if (boardState.available_pos.includes(pos_id)) {
      if (selected_pawns.length === 1) selected_pawns = selected_pawns[0];
      setBoardState({
        ...boardState,
        current_move: [...boardState.current_move, [selected_pawns, pos_id]],
        selected_pawns: [],
      });
    }
  };

  return (
    // Layout of the Board
    <div className="board-info-container">
      <div className="board-container">
        <div className="colour-container red-container">
          <Base
            colour="red"
            id="R"
            boardState={boardState}
            handlePawnClick={handlePawnClick}
            handlePosClick={handlePosClick}
          />
        </div>
        <PContainer
          orientation={"vert"}
          colours={["", "", "", "", "", ""]}
          ids={["P12", "P11", "P10", "P9", "P8", "P7"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <PContainer
          orientation={"vert"}
          colours={["", "green", "green", "green", "green", "green"]}
          ids={["P13", "GH1", "GH2", "GH3", "GH4", "GH5"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <PContainer
          orientation={"vert"}
          colours={["", "green", "", "", "", ""]}
          ids={["P14", "P15", "P16", "P17", "P18", "P19"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <div className="colour-container green-container">
          <Base
            colour="green"
            id="G"
            boardState={boardState}
            handlePawnClick={handlePawnClick}
            handlePosClick={handlePosClick}
          />
        </div>
        <PContainer
          orientation={"hor"}
          colours={["", "red", "", "", "", ""]}
          ids={["P1", "P2", "P3", "P4", "P5", "P6"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <Pos
          container_colour="green"
          classes="middle-winner"
          id="GH6"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <PContainer
          orientation={"hor"}
          colours={["", "", "", "", "", ""]}
          ids={["P20", "P21", "P22", "P23", "P24", "P25"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <PContainer
          orientation={"hor"}
          colours={["", "red", "red", "red", "red", "red"]}
          ids={["P52", "RH1", "RH2", "RH3", "RH4", "RH5"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <Pos
          container_colour="red"
          id="RH6"
          classes="middle-winner"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <Pos
          container_colour="yellow"
          id="YH6"
          classes="middle-winner"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <PContainer
          orientation={"hor"}
          colours={["yellow", "yellow", "yellow", "yellow", "yellow", ""]}
          ids={["YH5", "YH4", "YH3", "YH2", "YH1", "P26"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <PContainer
          orientation={"hor"}
          colours={["", "", "", "", "", ""]}
          ids={["P51", "P50", "P49", "P48", "P47", "P46"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <Pos
          container_colour="blue"
          id="BH6"
          classes="middle-winner"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <Pos
          container_colour="disabled"
          id=""
          classes="middle-winner"
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></Pos>
        <PContainer
          orientation={"hor"}
          colours={["", "", "", "", "yellow", ""]}
          ids={["P32", "P31", "P30", "P29", "P28", "P27"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <div className="colour-container blue-container">
          <Base
            colour="blue"
            id="B"
            boardState={boardState}
            handlePawnClick={handlePawnClick}
            handlePosClick={handlePosClick}
          />
        </div>
        <PContainer
          orientation={"vert"}
          colours={["", "", "", "", "blue", ""]}
          ids={["P45", "P44", "P43", "P42", "P41", "P40"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <PContainer
          orientation={"vert"}
          colours={["blue", "blue", "blue", "blue", "blue", ""]}
          ids={["BH5", "BH4", "BH3", "BH2", "BH1", "P39"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <PContainer
          orientation={"vert"}
          colours={["", "", "", "", "", ""]}
          ids={["P33", "P34", "P35", "P36", "P37", "P38"]}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        ></PContainer>
        <div className="colour-container yellow-container">
          <Base
            colour="yellow"
            id="Y"
            boardState={boardState}
            handlePawnClick={handlePawnClick}
            handlePosClick={handlePosClick}
          />
        </div>
      </div>
      <div className="info-container">Info</div>
    </div>
  );
};

export default Board;
