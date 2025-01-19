import { useContext } from "react";
import { assets } from "../../assets/assets";
import "./main.css";
import { Context } from "../../context/Context";
import React, { useState, useEffect, useRef } from "react";
import Dropdown from "../dropdown/Dropdown";
import { TypeAnimation } from 'react-type-animation';
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import remarkGfm from "remark-gfm";

const Main = () => {
	const {
		onRender,
		newChat,
		recentPrompt,
		showResults,
		setRecentPrompt,
		setShowResults,
		setResultData,
		setLoading,
		loading,
		resultData,
		setInput,
		input,
		evenData,
		setEvenData,
		graphData,
		setGraphData,
		downloadData,
		setDownloadData,
		socket,
		setSocket,
		agentData,
		setAgentData,
		setPrevResults,
		onRenderAgent,
		prevPrompts,
		setPrevPrompts,
		chatNo,
		setChatNo,
		fileHistory,
		setFileHistory,
		resp,
		isUpload,
		setIsUpload,

	} = useContext(Context);

	const resultDataRef = useRef(null); // Reference to the result-data container for auto scrolling
	const agentDataRef = useRef(null);
	const agent = useRef(true);

	const [markdownContent, setMarkdownContent] = useState('');
	const [reccQs, setReccQs] = useState([])
	const [isChecked, setIsChecked] = useState(false);
	const [isDropdownOpen, setIsDropdownOpen] = useState(false);

	const ToggleSwitch = ({ label }) => {

		const handleToggle = () => {
			setIsChecked(!isChecked);
			let query = !isChecked
			if (socket && socket.readyState === WebSocket.OPEN) {
				socket.send(JSON.stringify({ type: 'toggleRag', query }));
			}
		};

		return (
			<div className="container">
				{label}{" "}
				<div className="toggle-switch">
					<input
						type="checkbox"
						className="checkbox"
						name={label}
						id={label}
						checked={isChecked} // Control checkbox based on state
						onChange={handleToggle} // Call handleToggle on checkbox change
					/>
					<label className="label" htmlFor={label}>
						<span className="inner" />
						<span className="switch" />
					</label>
				</div>
			</div>
		);
	};

	const textAreaRef = useRef(null);

	const generatePDF = () => {
		// Send the raw Markdown content to the backend
		fetch('http://127.0.0.1:5001/convert', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({ content: markdownContent }),
		})
			.then(response => {
				if (!response.ok) {
					throw new Error('Failed to send data to the backend');
				}
				return response.json(); // Expecting a JSON response
			})
			.then(data => {
				console.log('Markdown content sent successfully to backend:', data.message);

				// Now fetch the generated HTML from the backend after it's processed
				return fetch('http://127.0.0.1:5001/download-pdf', {
					method: 'GET',
				});
			})
			.then(response => {
				if (!response.ok) {
					throw new Error('Failed to fetch the generated HTML');
				}
				return response.text(); // Convert the response to plain text (HTML content)
			})
			.then(htmlContent => {
				// Open the HTML content in a new tab
				const newTab = window.open();
				if (newTab) {
					newTab.document.open();
					newTab.document.write(htmlContent);
					newTab.document.close();
				} else {
					console.error('Failed to open a new Tab')
				}

			})
			.catch(error => {
				console.error('Error during the process:', error);
			});
	};

	// Auto-scrolling effect when resultData changes
	useEffect(() => {
		if (resultDataRef.current) {
			resultDataRef.current.scrollTop = resultDataRef.current.scrollHeight;
		}
	}, [resultData]);
	useEffect(() => {
		if (agentDataRef.current) {
			agentDataRef.current.scrollTop = agentDataRef.current.scrollHeight;
		}
	}, [agentData]);


	const handleCardClick = (promptText) => {
		setInput(promptText);
	};

	const handleClick = () => {
		setInput("");
		setResultData("")
		setShowResults(true);
		setLoading(true);
		setDownloadData(false)
		resp.current = true;
		setRecentPrompt(input);
		if (chatNo == 0)
			setPrevPrompts(prev => [...prev, input]);
		setChatNo(chatNo + 1);

		let query = input;
		console.log(query);
		// if (socket && socket.readyState === WebSocket.OPEN) {
		// 	socket.send(JSON.stringify({ type: 'query', query }));
		// }
		try {
			fetch('http://127.0.0.1:8080/query', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ query: input }), // Send input to the Flask backend
			}).then((response) => {
				if (!response.ok) {
					throw new Error('Failed to send query to backend');
				}
				return response.json(); // Expecting a JSON response
			}
			).then((data) => {
				console.log('Query sent successfully:', data);
				setResultData(data.message);
				onRender(data.message);
				setLoading(false);
				console.log(resultData);
			}
			)
		} catch (error) {
			console.error('Error sending query to backend:', error);
			setLoading(false);
		}
	}

	// Adjust textarea height dynamically
	const adjustHeight = () => {
		const textArea = textAreaRef.current;

		// Reset the height to auto to shrink it before resizing
		textArea.style.height = 'auto';

		// Adjust the height based on scrollHeight
		textArea.style.height = `${textArea.scrollHeight}px`;

		// Move the textarea upwards by adjusting margin-top dynamically
		const diff = textArea.scrollHeight - textArea.clientHeight;
	};

	// Adjust height when input changes
	useEffect(() => {
		adjustHeight();
	}, [input]);

	const handleFileChange = async (event) => {
		const files = event.target.files;
		await setEvenData(event);

		if (files.length > 0) {
			const formData = new FormData();

			// Append each selected file to the FormData object
			for (let i = 0; i < files.length; i++) {
				formData.append('file', files[i]);

				// Update fileHistory state by adding new file info
				setFileHistory((prevFileHistory) => [
					...prevFileHistory,
					{
						fileName: files[i].name,
						fileSize: files[i].size,
						fileType: files[i].type,
						timestamp: new Date().toLocaleString(),
					},
				]);
				
				try {
					// Send a POST request
					const response = await fetch('http://127.0.0.1:8080/upload', {
						method: 'POST',
						body: formData,
					});

					if (response.ok) {
						const result = await response.json();
						console.log('Files uploaded successfully:', result);
						setIsUpload(true);
						setTimeout(() => {
							setIsUpload(false);
						}, 1000);
						// Update file history after successful upload


					} else {
						console.error('Error uploading files:', response.statusText);
					}
				} catch (error) {
					console.error('Error during upload:', error);
				}
			}
		};
		setIsDropdownOpen(false)
	}

	const triggerFileInput = () => {
		document.getElementById('hiddenFileInput').click(); // Programmatically trigger click on hidden input
	};

	// Toggle the dropdown visibility
	const toggleDropdown = () => {
		setIsDropdownOpen(!isDropdownOpen);
	};

	// Close the dropdown
	const closeDropdown = () => {
		setIsDropdownOpen(false);
	};

	// Close the dropdown if the user clicks outside of it
	window.onclick = function (event) {
		const dropdown = document.getElementById("dropdown");
		const buttonContainer = document.querySelector(".button-container");

		// Check if the clicked element is not the dropdown or the button
		if (dropdown && buttonContainer && !buttonContainer.contains(event.target)) {
			dropdown.style.display = "none";
		}
	};

	console.log("Rendering resultData:", resultData)

	return (

		<div className="main" tabIndex="0" onKeyDown={(e) => {
			if (e.key === 'Enter' && !resp.current) {
				e.preventDefault();
				handleClick();
			}
		}}>
			<div className="nav">

				<img src={assets.UPpolice_logo} className="uppLogo" alt="" />
				<div className="rightside">
					<Dropdown />
					<ToggleSwitch label={"Docs"} />
				</div>
			</div>
			<div className="main-content">
				<div className="main-container" >
					{!showResults ? (
						<>
							<div className="contain">
								<div className="greet">
									<TypeAnimation
										sequence={[
											'Hello, Officer!'
										]}
										speed={{ type: 'keyStrokeDelayInMs', value: 100 }}
										style={{ fontSize: '1em' }}
									/>
									<p style={{ fontSize: '0.75em' }}>How can I help you today?</p>
								</div>
								<div className="cards">
									<div
										className="card"
										onClick={() =>
											handleCardClick("What is the jurisdiction of the Uttar Pradesh Police?")
										}
									>
										<p style={{ textAlign: "justify" }}>What is the jurisdiction of the Uttar Pradesh Police?</p>
									</div>
									<div
										className="card"
										onClick={() => {
											handleCardClick(
												"Communication related query"
											);
										}}
									>
										<p style={{ textAlign: "justify" }}>Communication related query</p>
									</div>
									<div
										className="card"
										onClick={() =>
											handleCardClick(
												"Communication related query"
											)
										}
									>
										<p style={{ textAlign: "justify" }}>
											Communication related query</p>
									</div>
									<div
										className="card"
										onClick={() =>
											handleCardClick("Communication related query")
										}
									>
										<p style={{ textAlign: "justify" }}>Communication related query</p>
									</div>
								</div>
							</div>

						</>
					) : (
						<div className="result">
							<div className="result-title">
								<p>{recentPrompt}</p>
							</div>
							<div>
								{!loading && (
									<div className="result-data" ref={resultDataRef} style={{ overflowY: 'auto', maxHeight: '400px' }}>
										<img src={assets.satyamev_icon} className="satyamev-res" alt="" />
										<div className="markdown-content">
											<ReactMarkdown
												rehypePlugins={[rehypeRaw]}
												remarkPlugins={[remarkGfm]}
												components={{
													a: ({ href, children }) => (
														<a href={href} target="_blank" rel="noopener noreferrer">
															{children}
														</a>
													)
												}}
											>
												{resultData}
											</ReactMarkdown>
										</div>
									</div>
								)}
								{downloadData &&
									<div className="result-data" ref={agentDataRef} style={{ overflow: 'auto' }}>
										<img src={assets.download_icon} onClick={generatePDF} style={{ width: '20px', marginTop: '1vh', marginLeft: '7vh' }} />
									</div>

								}

								{downloadData && <h1 className="result-data" style={{ marginBottom: '10px' }}>Recommended Questions</h1>}
								<div className="result-data" ref={agentDataRef} style={{ display: 'flex', gap: '10px' }}>
									{downloadData &&
										<div
											className="card"
											style={{
												minHeight: '10vh',
												width: '33%',  // Allow each card to take up to 33% of the width
												marginRight: '20px',
												display: 'flex',  // Ensure the card uses flexbox
												flexDirection: 'column',  // Align content vertically
												justifyContent: 'center',  // Center the text vertically within the card
												alignItems: 'center',  // Center text horizontally
												overflow: 'hidden',  // Hide overflow if text exceeds the card's boundaries
												//wordWrap: 'break-word',  // Break long words if needed to fit inside the card
												textOverflow: 'ellipsis',  // Show ellipsis if the text is too long
											}}
											onClick={() => handleCardClick(reccQs[0])}
										>
											<p style={{ textAlign: "left", fontSize: '15px', margin: '0px 6px', padding: '2px' }}>{reccQs[0]}</p>
										</div>
									}

									{downloadData &&
										<div
											className="card"
											style={{
												minHeight: '10vh',
												width: '33%',  // Allow each card to take up to 33% of the width
												marginRight: '20px',
												display: 'flex',
												flexDirection: 'column',
												justifyContent: 'center',
												alignItems: 'center',
												overflow: 'hidden',  // Hide overflow if text exceeds the card's boundaries
												//wordWrap: 'break-word',  // Break long words if needed to fit inside the card
												textOverflow: 'ellipsis',  // Show ellipsis if the text is too long
											}}
											onClick={() => handleCardClick(reccQs[1])}
										>
											<p style={{ textAlign: "left", fontSize: '15px', margin: '0px 6px', padding: '2px' }}>{reccQs[1]}</p>
										</div>
									}

									{downloadData &&
										<div
											className="card"
											style={{
												minHeight: '10vh',
												width: '33%',  // Allow each card to take up to 33% of the width
												display: 'flex',
												flexDirection: 'column',
												justifyContent: 'center',
												alignItems: 'center',
												overflow: 'hidden',  // Hide overflow if text exceeds the card's boundaries
												// wordWrap: 'break-word',  // Break long words if needed to fit inside the card
												textOverflow: 'ellipsis',  // Show ellipsis if the text is too long
											}}
											onClick={() => handleCardClick(reccQs[2])}
										>
											<p style={{ textAlign: "left", fontSize: '15px', margin: '0px 6px', padding: '2px' }}>{reccQs[2]}</p>
										</div>
									}
								</div>

							</div>


						</div>
					)}
				</div>
				<div className="main-bottom">
					<div className="search-box">
						<textarea
							ref={textAreaRef}
							onChange={(e) => setInput(e.target.value)}
							value={input}
							placeholder="Enter the Prompt Here"
							rows={1} // Start with 1 row
							style={{
								position: 'relative',
								background: '#f0f4f9',
								outline: 'none',
								border: 'none',
								width: '100%',
								minHeight: '40px', // Minimum height for the textarea
								maxHeight: '100px',
								resize: 'none', // Disable manual resize by the user
								overflow: 'hidden', // Hide overflow to prevent scrollbars
								fontSize: '16px', // Adjust font size as needed
								borderRadius: '5px', // Rounded corners for style
							}}
						/>
						<div>
							<img src={assets.attach_icon} className="upload" onClick={!resp.current ? toggleDropdown : null} />
							<img
								src={assets.send_icon}
								alt=""
								onClick={!resp.current ? handleClick : null}
							/>
						</div>
					</div>
					<div className="bottom-info">
						<p></p>
					</div>
				</div>
				{/* Overlay and Dropdown */}
				{isDropdownOpen && (
					<>
						{/* Overlay */}
						<div className="overlay" onClick={closeDropdown}></div>

						{/* Dropdown Content */}
						<div id="dropdown" className="dropdown-content">
							<div>
								<button onClick={triggerFileInput}>Upload from Computer</button>
								<input
									multiple
									id="hiddenFileInput"
									type="file"
									style={{ display: "none" }}
									onChange={handleFileChange}
								/>
							</div>
							<a
								href="https://drive.google.com/drive/folders/1bmB1oKZ3J8_Onbd-pQKbhiBDLi8AGls9"
								target="_blank"
								rel="noopener noreferrer"
							>
								<button onClick={closeDropdown}>Upload to Google Drive</button>
							</a>
						</div>
					</>
				)}
			</div>
		</div>
	);
};

export default Main;