import Main from "./components/main/Main";
import Sidebar from "./components/sidebar/Sidebar";
import GraphBar from "./components/graphbar/Graphbar";
import  ContextProvider from './context/Context';  // Import ContextProvider

const App = () => {
  return (
    <ContextProvider>  {/* Wrap everything inside ContextProvider */}
      <Sidebar />
      <Main />
      <GraphBar />
      {/* <Popup /> */}
    </ContextProvider>
  );
};

export default App;
