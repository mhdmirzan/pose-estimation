import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Image, Video, Upload, Download, RefreshCw, Activity, Linkedin } from 'lucide-react';
import UploadSection from './components/UploadSection';
import './App.css';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.startsWith('192.168.')
  ? `http://${window.location.hostname}:8000/api`
  : '/api';

function App() {
  const [activeTab, setActiveTab] = useState('image');
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sampleImages, setSampleImages] = useState([]);
  const [sampleVideos, setSampleVideos] = useState([]);
  const [selectedSample, setSelectedSample] = useState('');

  useEffect(() => {
    fetchSamples();
  }, []);

  const fetchSamples = async () => {
    try {
      const [imagesRes, videosRes] = await Promise.all([
        axios.get(`${API_BASE}/samples/images`),
        axios.get(`${API_BASE}/samples/videos`)
      ]);
      setSampleImages(imagesRes.data.files || []);
      setSampleVideos(videosRes.data.files || []);
    } catch (err) {
      console.error('Failed to fetch samples:', err);
    }
  };

  const handleFileSelect = (selectedFile) => {
    setFile(selectedFile);
    setPreviewUrl(URL.createObjectURL(selectedFile));
    setResultUrl(null);
    setError(null);
    setSelectedSample('');
    processFile(selectedFile);
  };

  const processFile = async (fileToProcess) => {
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', fileToProcess);

    try {
      const endpoint = activeTab === 'image' ? '/predict/image' : '/predict/video';
      const response = await axios.post(`${API_BASE}${endpoint}`, formData, {
        responseType: 'blob',
        timeout: 65000,
      });

      const url = URL.createObjectURL(response.data);
      setResultUrl(url);
    } catch (err) {
      console.error(err);
      if (err.code === 'ECONNABORTED') {
        setError('Processing timed out (max 1 min). Please try a shorter video.');
      } else {
        setError('Error processing file. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const processSample = async (filename) => {
    if (!filename) return;

    setLoading(true);
    setError(null);
    setSelectedSample(filename);
    setFile(null);
    setResultUrl(null);

    try {
      const BACKEND_URL = API_BASE.replace('/api', '');
      const previewPath = activeTab === 'image'
        ? `${BACKEND_URL}/samples/images/${filename}`
        : `${BACKEND_URL}/samples/videos/${filename}`;
      setPreviewUrl(previewPath);

      const endpoint = activeTab === 'image'
        ? `/predict/sample/image/${filename}`
        : `/predict/sample/video/${filename}`;

      const method = activeTab === 'image' ? 'get' : 'post';
      const response = await axios({
        method,
        url: `${API_BASE}${endpoint}`,
        responseType: 'blob',
        timeout: 65000,
      });

      const url = URL.createObjectURL(response.data);
      setResultUrl(url);
    } catch (err) {
      console.error(err);
      if (err.code === 'ECONNABORTED') {
        setError('Processing timed out (max 1 min). Please try a shorter video.');
      } else {
        setError('Error processing sample. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setPreviewUrl(null);
    setResultUrl(null);
    setError(null);
    setSelectedSample('');
  };

  const samples = activeTab === 'image' ? sampleImages : sampleVideos;

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <Activity size={32} strokeWidth={2.5} />
          <div>
            <h1>FlexAnalyze</h1>
            <span className="header-subtitle">Advanced Video & Image Pose Detection</span>
          </div>
        </div>
        <nav className="header-nav">
          <button
            className={`nav-btn ${activeTab === 'image' ? 'active' : ''}`}
            onClick={() => { setActiveTab('image'); reset(); }}
          >
            <Image size={20} />
            Image
          </button>
          <button
            className={`nav-btn ${activeTab === 'video' ? 'active' : ''}`}
            onClick={() => { setActiveTab('video'); reset(); }}
          >
            <Video size={20} />
            Video
          </button>
        </nav>
      </header>

      {/* Main Content - Full Width */}
      <main className="main-content">
        <div className="content-header">
          <div className="title-section">
            <h2>{activeTab === 'image' ? 'Image' : 'Video'} Pose Analysis</h2>
            <p>Upload your own file or select from samples</p>
          </div>
          <div className="sample-section">
            <label>Test Samples:</label>
            <select
              className="sample-dropdown"
              value={selectedSample}
              onChange={(e) => processSample(e.target.value)}
              disabled={loading}
            >
              <option value="">-- Select a {activeTab} --</option>
              {samples.map((file) => (
                <option key={file} value={file}>{file}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="content-body">
          {!previewUrl ? (
            <div className="upload-area">
              <UploadSection
                onUpload={handleFileSelect}
                type={activeTab}
                isLoading={loading}
              />
            </div>
          ) : (
            <div className="result-area">
              <div className="result-actions">
                <button className="btn btn-outline" onClick={reset}>
                  <RefreshCw size={18} />
                  New Analysis
                </button>
                {resultUrl && (
                  <a
                    href={resultUrl}
                    download={`pose_result.${activeTab === 'image' ? 'jpg' : 'mp4'}`}
                    className="btn btn-primary"
                  >
                    <Download size={18} />
                    Download Result
                  </a>
                )}
              </div>

              {error && <div className="error-msg">{error}</div>}

              <div className="comparison-view">
                {/* Original */}
                <div className="media-panel">
                  <h3>Original</h3>
                  <div className="media-wrapper">
                    {activeTab === 'image' ? (
                      <img src={previewUrl} alt="Original" />
                    ) : (
                      <video src={previewUrl} controls />
                    )}
                  </div>
                </div>

                {/* Result */}
                <div className="media-panel">
                  <h3>Pose Estimation Result</h3>
                  <div className="media-wrapper">
                    {loading ? (
                      <div className="loading-container">
                        <div className="loading-spinner"></div>
                        <p>Processing{activeTab === 'video' ? ' video (this may take a while)' : ''}...</p>
                      </div>
                    ) : resultUrl ? (
                      activeTab === 'image' ? (
                        <img src={resultUrl} alt="Result" />
                      ) : (
                        <video src={resultUrl} controls autoPlay loop />
                      )
                    ) : (
                      <div className="placeholder">
                        <p>Result will appear here</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <p>Powered by Ultralytics YOLOv11 • Built with FastAPI & React</p>
          <div className="footer-divider"></div>
          <div className="creator-info">
            <span>Created by <strong>Mohammed Mirzan</strong></span>
            <a
              href="https://www.linkedin.com/in/mirzan-fawas/"
              target="_blank"
              rel="noopener noreferrer"
              className="social-link"
            >
              <Linkedin size={18} />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
