import React, { useContext } from "react";
import { Context } from "../../context/Context";

const Dropdown = () => {
    const {
      language,
      setLanguage
  
    } = useContext(Context);

  // Handle dropdown change
  const handleChange = (event) => {
    setLanguage(event.target.value);
  };

  return (
    <div style={styles.container}>
      <select value={language} onChange={handleChange} style={styles.dropdown}>
        <option value="english">English</option>
        <option value="hindi">Hindi</option>
      </select>
    </div>
  );
};

// Inline styles
const styles = {
  container: {
    textAlign: "center",
    margin: "10px",
    maxWidth: "1200px",
  },
  dropdown: {
    padding: "10px",
    fontSize: "16px",
    width: "100%",
    borderRadius: "5px",
    border: "1px solid #ddd",
    outline: "none",
  },
  result: {
    marginTop: "20px",
    fontSize: "16px",
    color: "#333",
  },
};

export default Dropdown;