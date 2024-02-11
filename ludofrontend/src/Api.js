import axios from "axios";

// const API_URL = "http://127.0.0.1:5000";
const API_URL = "http://192.168.207.118:5000";

const getCurrentBoard = () => {
  return axios.get(API_URL + "/get_current_board");
};

const checkRunningGame = () => {
  return axios.get(API_URL + "/check_running_game");
};
const reset = () => {
  return axios.get(API_URL + "/reset");
};
const createNewGame = (data) => {
  return axios.post(API_URL + "/create_new_game", data);
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
  getCurrentBoard,
  checkRunningGame,
  reset,
  createNewGame,
  postMove,
  getLogFilenames,
  getLogFile,
};

export default apiFunctions;
