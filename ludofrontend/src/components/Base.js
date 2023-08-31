import React from "react";
import Pos from "./Pos";

const Base = ({ colour, id, boardState }) => {
  return (
    <div className="inner-colour-container">
      {[1, 2, 3, 4].map((num) => (
        <Pos
          classes={`base-pos-container`}
          container_colour={colour}
          id={`${id}B${num}`}
          boardState={boardState}
        />
      ))}
    </div>
  );
};

export default Base;
