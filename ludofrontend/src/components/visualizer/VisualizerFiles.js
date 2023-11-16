import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Api from "../../Api";
const VisualizerFiles = () => {
  const [files, setFiles] = useState([]);
  const [run, setRun] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    Api.getLogFilenames(100)
      .then((res) => {
        setFiles(res.data);
      })
      .catch((err) => {
        console.log(err);
      });
  }, []);

  const handleRunClick = (run_index) => {
    setRun(files[run_index].run);
    setSelectedFiles(files[run_index].files);
  };

  const handleFileClick = (filename) => {
    navigate(`/vis/${run}/${filename}`);
  };

  return (
    <section className="board-section">
      <div className="visualizer-file-container">
        <div className="card run-container">
          <h5>Select from an available run:</h5>
          <div className="runs">
            {files.map((elem, index) => (
              <div
                key={index}
                className="btn btn-blue"
                onClick={() => handleRunClick(index)}
              >
                <h6>{elem.run}</h6>
              </div>
            ))}
          </div>
        </div>
        <div className="card run-container">
          {!run ? (
            <h5>No Run Selected</h5>
          ) : (
            <>
              <h5>Available Log Files for {run}:</h5>
              <div className="runs">
                {selectedFiles.map((elem, index) => (
                  <div
                    key={index}
                    className="btn btn-green"
                    onClick={() => handleFileClick(elem)}
                  >
                    <h6>{elem}</h6>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
};

export default VisualizerFiles;
