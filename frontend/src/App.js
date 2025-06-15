import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import PDFUploader from './PDFUploader';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<PDFUploader />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App; 