import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faStar, faTrophy } from "@fortawesome/free-solid-svg-icons";
import Pawn from "./Pawn";
const Pos = ({ classes, container_colour, id, boardState }) => {
  const extractPawnsAtPos = () => {
    let pawns = [];
    for (let i = 0; i < boardState.positions.length; i++) {
      if (boardState.positions[i].pos_id === id)
        pawns.push(boardState.positions[i].pawn_id);
    }
    return pawns;
  };
  return (
    <div className={`pos-container ${classes} ${container_colour}-container`}>
      {["P2", "P10", "P15", "P23", "P28", "P36", "P41", "P49"].indexOf(id) >
      -1 ? (
        <div className="star">
          <FontAwesomeIcon icon={faStar} />
        </div>
      ) : null}
      {["RH6", "GH6", "YH6", "BH6"].indexOf(id) > -1 ? (
        <div className="star">
          <FontAwesomeIcon icon={faTrophy} />
        </div>
      ) : null}

      {extractPawnsAtPos().map((pawn_id, index) => (
        <Pawn number={index + 1} id={pawn_id} boardState={boardState} />
      ))}
      <small>{id}</small>
    </div>
  );
};

export default Pos;
