import React, { useState } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

const PDFUploader = () => {
  const [file, setFile] = useState(null);
  const [parser, setParser] = useState('pypdf');
  const [processing, setProcessing] = useState(false);
  const [documents, setDocuments] = useState([]);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleParserChange = (event) => {
    setParser(event.target.value);
  };

  const uploadFile = async () => {
    if (!file) return;

    setProcessing(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('parser', parser);

    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const newDoc = {
        id: response.data.doc_id,
        filename: file.name,
        status: 'processing',
      };

      setDocuments([newDoc, ...documents]);
      pollStatus(newDoc.id);
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setProcessing(false);
      setFile(null);
    }
  };

  const pollStatus = async (docId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/status/${docId}`);
        const status = response.data.status;

        setDocuments((prevDocs) =>
          prevDocs.map((doc) =>
            doc.id === docId
              ? {
                  ...doc,
                  status,
                  content: response.data.content,
                  summary: response.data.summary,
                }
              : doc
          )
        );

        if (status === 'completed' || status === 'error') {
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Error polling status:', error);
        clearInterval(pollInterval);
      }
    }, 2000);
  };

  const renderDocumentContent = (doc) => {
    if (doc.status !== 'completed') {
      return (
        <Typography component="span" variant="body2" color="text.primary">
          Status: {doc.status}
        </Typography>
      );
    }

    return (
      <Box sx={{ mt: 2 }}>
        <Box sx={{ mb: 2 }}>
          <Typography variant="h6" component="h3" gutterBottom>
            Summary:
          </Typography>
          <Typography variant="body2">
            {doc.summary}
          </Typography>
        </Box>
        <Box>
          <Typography variant="h6" component="h3" gutterBottom>
            Content:
          </Typography>
          <Paper sx={{ p: 2 }}>
            <ReactMarkdown>{doc.content}</ReactMarkdown>
          </Paper>
        </Box>
      </Box>
    );
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          PDF Processor
        </Typography>
        <Box sx={{ mb: 3 }}>
          <input
            accept=".pdf"
            style={{ display: 'none' }}
            id="raised-button-file"
            type="file"
            onChange={handleFileChange}
          />
          <label htmlFor="raised-button-file">
            <Button variant="contained" component="span" sx={{ mr: 2 }}>
              Choose PDF
            </Button>
          </label>
          {file && (
            <Typography component="span" variant="body1">
              Selected: {file.name}
            </Typography>
          )}
        </Box>
        <FormControl sx={{ minWidth: 200, mb: 2 }}>
          <InputLabel>Parser</InputLabel>
          <Select value={parser} label="Parser" onChange={handleParserChange}>
            <MenuItem value="pypdf">PyPDF</MenuItem>
            <MenuItem value="gemini">Google Gemini</MenuItem>
          </Select>
        </FormControl>
        <Box>
          <Button
            variant="contained"
            color="primary"
            onClick={uploadFile}
            disabled={!file || processing}
          >
            {processing ? <CircularProgress size={24} /> : 'Upload and Process'}
          </Button>
        </Box>
      </Paper>

      <List>
        {documents.map((doc) => (
          <React.Fragment key={doc.id}>
            <ListItem alignItems="flex-start">
              <ListItemText
                primary={doc.filename}
                secondary={renderDocumentContent(doc)}
              />
            </ListItem>
            <Divider component="li" />
          </React.Fragment>
        ))}
      </List>
    </Container>
  );
};

export default PDFUploader; 