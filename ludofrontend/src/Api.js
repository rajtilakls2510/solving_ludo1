import axios from "axios";

const API_URL = "http://127.0.0.1:5000";

const getState = () => {
  return axios.get(API_URL + "/state");
};

const postMove = (data) => {
  return axios.post(API_URL + "/take_move", data);
};

const getLogFilenames = (num) => {
  return axios.get(API_URL + "/get_logs?num_files=" + num);
};

const getLogFile = (run, filename) => {
  return axios.get(API_URL + `/get_log_file?run=${run}&file=${filename}`);
};

const apiFunctions = {
  getState,
  postMove,
  getLogFilenames,
  getLogFile,
};

export default apiFunctions;
