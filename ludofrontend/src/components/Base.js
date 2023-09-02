import React from "react";
import Pos from "./Pos";

const Base = ({ colour, id, boardState, handlePawnClick, handlePosClick }) => {
  return (
    <div className="inner-colour-container">
      {[1, 2, 3, 4].map((num) => (
        <Pos
          key={`${id}B${num}`}
          classes={`base-pos-container`}
          container_colour={colour}
          id={`${id}B${num}`}
          boardState={boardState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        />
      ))}
    </div>
  );
};

export default Base;
