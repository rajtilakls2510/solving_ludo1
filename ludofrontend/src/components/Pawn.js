import React from "react";

const Pawn = ({ number, id, boardState = { boardState } }) => {
  return (
    <button className={`btn pawn-1 pawn-${number} btn-${boardState.pawns[id]}`}>
      {" "}
    </button>
  );
};

export default Pawn;
