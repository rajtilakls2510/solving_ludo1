import React from "react";
import { Tooltip } from "react-tooltip";

const Pawn = ({ number, id, boardState, playerState, handlePawnClick }) => {
  return (
    <button
      className={`btn pawn-1 pawn-${number} btn-${
        boardState.pawns[id].colour
      } btn-${boardState.pawns[id].colour}-${
        playerState.selected_pawns.includes(id) ? "selected" : ""
      }`}
      onClick={() => handlePawnClick(id)}
      data-tooltip-id="pawn-tooltip"
      data-tooltip-content={`${id}`}
    >
      <small>{id}</small>
      <Tooltip id="pawn-tooltip" />
    </button>
  );
};

export default Pawn;
