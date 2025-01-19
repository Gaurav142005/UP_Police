import Main from "./components/main/Main";
import Sidebar from "./components/sidebar/Sidebar";
import  ContextProvider from './context/Context';

const App = () => {
  return (
    <ContextProvider>  {/* Wrap everything inside ContextProvider */}
      <Sidebar />
      <Main />
    </ContextProvider>
  );
};

export default App;
