import React from "react";
import Pos from "./Pos";

const PContainer = ({ orientation, colours, ids, boardState }) => {
  return (
    <div className={`length-container ${orientation}-container`}>
      {colours.map((colour, index) => (
        <Pos
          container_colour={colour}
          id={ids[index]}
          boardState={boardState}
        />
      ))}
    </div>
  );
};

export default PContainer;
