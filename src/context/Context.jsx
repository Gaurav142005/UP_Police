import { createContext, useState, useRef } from "react";
import runChat from "../config/Gemini";

export const Context = createContext();


const ContextProvider = (props) => {
	const [input, setInput] = useState("");
	const [recentPrompt, setRecentPrompt] = useState("");
	const [prevPrompts, setPrevPrompts] = useState([]);
	const [showResults, setShowResults] = useState(false);
	const [loading, setLoading] = useState(false);
	const [resultData, setResultData] = useState("");
	const [agentData, setAgentData] = useState("");
	const [graphData, setGraphData] = useState();
	const [socket, setSocket] = useState(null);
	const [evenData, setEvenData] = useState();
	const [downloadData, setDownloadData] = useState(false);
	const [chatNo, setChatNo] = useState(0);
	const displayedCharsRef = useRef(0); // Use a ref to track displayed characters count
	const totalCharsRef = useRef(0); // Use a ref for total characters
	const [fileHistory, setFileHistory] = useState([]);		// State to store the file history
	const [isUpload, setIsUpload] = useState(false);		// State to check if the user is uploading a file
	const [totalDisplayedCharsRef, setTotalDisplayedCharsRef] = useState(0); // State to track total displayed chars
	const [prevResults, setPrevResults] = useState([]);
	const pendingDataRef = useRef([]);
	const [language, setLanguage] = useState("english");
	const resp = useRef(false);

	// Helper function to update displayed characters and check if all have been shown
	const delayPara = (index, nextWord) => {
		setTimeout(function () {
			setResultData((prev) => prev + nextWord); // Append nextWord to resultData
			displayedCharsRef.current += 1; 
			// Check if all characters are displayed
			if (displayedCharsRef.current === totalCharsRef.current) {
				// All characters are shown, so set downloadData to true
				console.log('All characters displayed. Setting downloadData to true');
				setDownloadData(true);
				// setAgent(false);
				resp.current = false;
			}
		}, 0.5 * index); // Slower pace for better visibility
	};
	const delayParaAgent = (index, nextWord) => {
		setTimeout(function () {
			setAgentData((prev) => prev + nextWord); // Append nextWord to resultData
			displayedCharsRef.current += 1;
	
			// Check if all characters are displayed for this batch
			if (displayedCharsRef.current === totalCharsRef.current) {
				console.log('All characters displayed for the current batch.');
				if (pendingDataRef.current.length > 0) {
					// Start rendering the next batch if there's more pending data
					renderBatch();
				} else {
					console.log('All data rendered. Setting downloadData to true.');
					// setDownloadData(true);
				}
			}
		}, 1 * index); // Adjust delay for desired pacing
	};

	// Function to reset the states for a new chat
	const newChat = () => {
		setLoading(false);
		setShowResults(false);
		setDownloadData(false);
		setChatNo(0);
		displayedCharsRef.current = 0; // Reset ref for displayed characters
	};

	const renderBatch = () => {
		const newChunk = pendingDataRef.current.shift(); // Get the next chunk
		if (!newChunk) return;
	
		totalCharsRef.current += newChunk.length; // Update the total characters count
		const newResponseArray = newChunk.split("");
	
		for (let i = 0; i < newResponseArray.length; i++) {
			const nextWord = newResponseArray[i];
			delayParaAgent(i, nextWord + "");
		}
	};

	// Function to handle sending the prompt
	const onSent = async (prompt, isAgent) => {
		setResultData("");
		setLoading(true);
		setShowResults(true);
		let response;
		if (isAgent === undefined) {
			if (prompt !== undefined) {
				response = await runChat(prompt);
				setRecentPrompt(prompt);
			} else {
				setPrevPrompts((prev) => [...prev, input]);
				setRecentPrompt(input);
				response = await runChat(input);
			}
		}

		try {
			let responseArray = response.split("**");
			let newResponse = "";
			for (let i = 0; i < responseArray.length; i++) {
				if (i === 0 || i % 2 !== 1) {
					newResponse += responseArray[i];
				} else {
					newResponse += "<b>" + responseArray[i] + "</b>";
				}
			}
			let newResponse2 = newResponse.split("*").join("<br/>");
			totalCharsRef.current = newResponse2.length; // Set the total chars to be displayed
			let newResponseArray = newResponse2.split("");
			for (let i = 0; i < newResponseArray.length; i++) {
				const nextWord = newResponseArray[i];
				delayPara(i, nextWord + "");
			}
		} catch (error) {
			console.error("Error while running chat:", error);
		} finally {
			setLoading(false);
			setInput("");
		}
	};

	// Function to render a pre-existing response
	const onRender = async (data) => {
		console.log('Rendering data:', data);
		console.log("Result data:", resultData);
		setResultData("");
		let response = data;
		try {
			// Split the response by '**' for bold formatting
			let responseArray = response.split("**");
			let newResponse = "";
			
			// Loop through the split parts and format the bold text
			for (let i = 0; i < responseArray.length; i++) {
				if (i === 0 || i % 2 !== 1) {
					newResponse += responseArray[i];
				} else {
					newResponse += "<b>" + responseArray[i] + "</b>"; // Apply bold to every second part
				}
			}
	
			// Replace '*' with <br/> for line breaks
			let newResponse2 = newResponse.split("*").join("<br/>");
	
			// Set the total length of the string for rendering
			totalCharsRef.current = newResponse2.length;
	
			// Split the final string into an array of characters
			let newResponseArray = newResponse2.split("");
	
			// Render each character with a delay
			setTotalDisplayedCharsRef(0);
			displayedCharsRef.current = 0;
	
			// Function to render each character one by one with delay
			for (let i = 0; i < newResponseArray.length; i++) {
				const nextChar = newResponseArray[i];
				delayPara(i, nextChar); // Delay function that will render each character
			}
		} catch (error) {
			console.error("Error while running chat:", error);
		} finally {
			// Set loading state to false when done rendering
			setLoading(false);
			setInput("");
		}
	};
	

	const onRenderAgent = async (data) => {
		try {
			// Split incoming data into formatted chunks
			const responseArray = data.split("**");
			let newResponse = "";
			for (let i = 0; i < responseArray.length; i++) {
				if (i === 0 || i % 2 !== 1) {
					newResponse += responseArray[i];
				} else {
					newResponse += "<b>" + responseArray[i] + "</b>";
				}
			}
			const formattedResponse = newResponse.split("*").join("<br/>");
	
			// Add the new chunk to the pending queue
			pendingDataRef.current.push(formattedResponse);
	
			// Start rendering if no other batch is currently being processed
			if (displayedCharsRef.current === totalCharsRef.current) {
				renderBatch();
			}
		} catch (error) {
			console.error("Error while rendering data:", error);
		} finally {
			setLoading(false);
			setInput("");
		}
	};

	const contextValue = {
		prevPrompts,
		setPrevPrompts,
		onSent,
		setShowResults,
		setRecentPrompt,
		setResultData,
		recentPrompt,
		input,
		onRender,
		setInput,
		showResults,
		prevResults,
    	setPrevResults,
		setLoading,
		loading,
		resultData,
		newChat,
		graphData,
		setGraphData,
		evenData,
		setEvenData,
		socket,
		setSocket,
		downloadData,
		setDownloadData,
		onRenderAgent,
		agentData,
		setAgentData,
		chatNo,
		setChatNo,
		fileHistory,
		setFileHistory,
		resp,
		isUpload,
		setIsUpload,
		language,
		setLanguage,
		totalDisplayedCharsRef,
		setTotalDisplayedCharsRef
	};

	return <Context.Provider value={contextValue}>{props.children}</Context.Provider>;
};

export default ContextProvider;