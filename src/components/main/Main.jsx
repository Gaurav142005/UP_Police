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
		agentData,
		prevPrompts,
		setPrevPrompts,
		chatNo,
		setChatNo,
		fileHistory,
		setFileHistory,
		resp,
		isUpload,
		setIsUpload,
		language,
		setLanguage
	} = useContext(Context);

	const resultDataRef = useRef(null); // Reference to the result-data container for auto scrolling
	const agentDataRef = useRef(null);

	const [markdownContent, setMarkdownContent] = useState('');
	const [isDropdownOpen, setIsDropdownOpen] = useState(false);

	const handleMarkdownChange = (e) => {
		setMarkdownContent(e.target.value);
	};

	const textAreaRef = useRef(null);

	const generatePDF = () => {
		// Send the raw Markdown content to the backend
		fetch('http://127.0.0.1:8080/convert', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({ content: markdownContent }),
		}).then(response => {
			if (!response.ok) {
				throw new Error('Failed to send data to the backend');
			}
			return response.json(); // Expecting a JSON response
		})
			.then(data => {
				console.log('Markdown content sent successfully to backend:', data.message);

				// Now fetch the generated HTML from the backend after it's processed
				return fetch('http://127.0.0.1:8080/download-pdf', { method: 'GET' });
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
		if (!input.trim()) return; // Prevent empty queries
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

		try {
			fetch('http://127.0.0.1:8080/query', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ query: input, lang: language }), // Send input to the Flask backend
			})
				.then((response) => {
					if (!response.ok) {
						throw new Error('Failed to send query to backend');
					}
					return response.json(); // Expecting a JSON response
				})
				.then((data) => {
					console.log('Query sent successfully:', data.message);

					setResultData(data.message);
					onRender(data.message);
					setMarkdownContent(data.message)
					setLoading(false);
				});

		} catch (error) {
			console.error('Error:', error);
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

	// Close the dropdown if the user clicks outside of it
	window.onclick = function (event) {
		const dropdown = document.getElementById("dropdown");
		const buttonContainer = document.querySelector(".button-container");

		// Check if the clicked element is not the dropdown or the button
		if (dropdown && buttonContainer && !buttonContainer.contains(event.target)) {
			dropdown.style.display = "none";
		}
	};

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
											handleCardClick("How can the UP Police help in conducting fear-free, independent and fair Lok Sabha elections?")
										}
									>
										<p style={{ textAlign: "justify", fontSize: '20px'}}>How can the UP Police help in conducting fear-free, independent and fair Lok Sabha elections?</p>
									</div>
									<div
										className="card"
										onClick={() => {
											handleCardClick(
												"What is the entry procedure into the Anti Narcotics Task Force?"
											);
										}}
									>
										<p style={{ textAlign: "justify", fontSize: '20px'}}>What is the entry procedure into the Anti Narcotics Task Force?</p>
									</div>
									<div
										className="card"
										onClick={() =>
											handleCardClick(
												"What is the procedure for police verification of applicants done by the concerned police station for issuing passports?"
											)
										}
									>
										<p style={{ textAlign: "justify", fontSize: '20px'}}>
										What is the procedure for police verification of applicants done by the concerned police station for issuing passports?
										</p>
									</div>
									<div
										className="card"
										onClick={() =>
											handleCardClick("What are the guidelines regarding effective prevention and safety of events happening with tourists?")
										}
									>
										<p style={{ textAlign: "justify", fontSize: '20px'}}>What are the guidelines regarding effective prevention and safety of events happening with tourists?</p>
									</div>
								</div>
							</div>

						</>
					) : (
						<div className="result">
							<div className="result-title">
								<img src={assets.satyamev_icon} className="satyamev-res" alt="" />
								<h2>{recentPrompt}</h2>
							</div>
							<div>
								{loading ? (
									<div className="loader">
										<hr />
										<hr />
										<hr />
									</div>
								) : (
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
											}}>{resultData}</ReactMarkdown>
									</div>
								)}
								{downloadData &&
									<div className="result-data" ref={agentDataRef} style={{ overflow: 'auto' }}>
										<img src={assets.download_icon} onClick={generatePDF} style={{ width: '20px', marginTop: '1vh', marginLeft: '7vh' }} />
									</div>

								}

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
							<div>
								<button onClick={triggerFileInput}></button>
								<input
									multiple
									id="hiddenFileInput"
									type="file"
									style={{ display: "none" }}
									onChange={handleFileChange}
								/>
							</div>
							<div>
								<button onClick={triggerFileInput} style={{ background: 'none', border: 'none' }}>
									<img src={assets.attach_icon} className="upload" />
									<input
										multiple
										id="hiddenFileInput"
										type="file"
										style={{ display: "none" }}
										onChange={handleFileChange}
									/>
								</button>
							</div>
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
			</div>
		</div>
	);
};

export default Main;