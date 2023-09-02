import React from "react";

const Pawn = ({ number, id, boardState, handlePawnClick }) => {
  return (
    <button
      className={`btn pawn-1 pawn-${number} btn-${
        boardState.pawns[id].colour
      } btn-${boardState.pawns[id].colour}-${
        boardState.selected_pawns.includes(id) ? "selected" : ""
      }`}
      onClick={() => handlePawnClick(id)}
    >
      <small>{id}</small>
    </button>
  );
};

export default Pawn;
