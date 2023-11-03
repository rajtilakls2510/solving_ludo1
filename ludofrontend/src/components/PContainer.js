import React from "react";
import Pos from "./Pos";

const PContainer = ({
  orientation,
  colours,
  ids,
  boardState,
  playerState,
  handlePawnClick,
  handlePosClick,
}) => {
  return (
    <div className={`length-container ${orientation}-container`}>
      {colours.map((colour, index) => (
        <Pos
          key={ids[index]}
          container_colour={colour}
          id={ids[index]}
          boardState={boardState}
          playerState={playerState}
          handlePawnClick={handlePawnClick}
          handlePosClick={handlePosClick}
        />
      ))}
    </div>
  );
};

export default PContainer;
