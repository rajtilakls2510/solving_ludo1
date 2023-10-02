import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import Api from "../../Api";
const VisualizerBoard = () => {
  const [info, setInfo] = useState(null);
  const { run, file } = useParams();
  useEffect(() => {
    Api.getLogFile(run, file)
      .then((res) => {
        setInfo(res.data);
      })
      .catch((err) => {
        console.log(err);
      });
  }, []);

  return <section className="board-section"></section>;
};

export default VisualizerBoard;
