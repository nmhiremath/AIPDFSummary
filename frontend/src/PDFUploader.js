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
  LinearProgress
} from '@mui/material';
import ReactMarkdown from 'react-markdown';

const PDFUploader = () => {
  const [file, setFile] = useState(null);
  const [parser, setParser] = useState('pypdf');
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [progress, setProgress] = useState('');

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('Please select a valid PDF file');
      setFile(null);
    }
  };

  const handleParserChange = (event) => {
    setParser(event.target.value);
  };

  const uploadFile = async () => {
    if (!file) return;

    setProcessing(true);
    setError(null);
    setProgress('Starting upload...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('parser', parser);

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      if (!data.doc_id) {
        throw new Error('No document ID received from server');
      }

      setProgress('Processing document...');

      // Poll for status updates
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`http://localhost:8000/status/${data.doc_id}`);
          if (!statusResponse.ok) {
            throw new Error('Failed to get status');
          }
          
          const statusData = await statusResponse.json();

          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            setProcessing(false);
            setProgress('');
            setDocuments(prev => [{
              id: data.doc_id,
              filename: file.name,
              ...statusData
            }, ...prev]);
          } else if (statusData.status === 'error') {
            clearInterval(pollInterval);
            setProcessing(false);
            setError(statusData.error || 'Processing failed');
            setProgress('');
          } else {
            setProgress(statusData.progress || 'Processing...');
          }
        } catch (error) {
          clearInterval(pollInterval);
          setProcessing(false);
          setError('Failed to get status updates');
          setProgress('');
        }
      }, 1000);
    } catch (error) {
      setProcessing(false);
      setError(error.message);
      setProgress('');
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          PDF Processor
        </Typography>
        
        <Box sx={{ mb: 3 }}>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Parser</InputLabel>
            <Select
              value={parser}
              label="Parser"
              onChange={handleParserChange}
            >
              <MenuItem value="pypdf">PyPDF</MenuItem>
              <MenuItem value="gemini">Google Gemini</MenuItem>
            </Select>
          </FormControl>
          
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            style={{ display: 'none' }}
            id="pdf-upload"
          />
          <label htmlFor="pdf-upload">
            <Button
              variant="contained"
              component="span"
              disabled={processing}
              sx={{ mr: 2 }}
            >
              Select PDF
            </Button>
          </label>
          {file && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Selected: {file.name}
            </Typography>
          )}
        </Box>

        <Box sx={{ mb: 3 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={uploadFile}
            disabled={!file || processing}
          >
            {processing ? <CircularProgress size={24} /> : 'Upload and Process'}
          </Button>
        </Box>

        {processing && (
          <Box sx={{ width: '100%', mb: 3 }}>
            <Typography variant="body2" gutterBottom>
              {progress}
            </Typography>
            <LinearProgress />
          </Box>
        )}

        {error && (
          <Typography color="error" sx={{ mb: 2 }}>
            {error}
          </Typography>
        )}

        {documents.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Processed Documents
            </Typography>
            <List>
              {documents.map((doc, index) => (
                <React.Fragment key={doc.id}>
                  {index > 0 && <Divider />}
                  <ListItem>
                    <ListItemText
                      primary={
                        <Box>
                          <Typography variant="subtitle1">
                            Status: {doc.status}
                          </Typography>
                          {doc.summary && (
                            <Paper sx={{ p: 2, mt: 1, mb: 2 }}>
                              <Typography variant="h6" gutterBottom>Summary</Typography>
                              <Typography variant="body1" style={{ whiteSpace: 'pre-line' }}>
                                {doc.summary}
                              </Typography>
                            </Paper>
                          )}
                          {doc.content && (
                            <Paper sx={{ p: 2 }}>
                              <Typography variant="h6" gutterBottom>Content</Typography>
                              <Box sx={{ 
                                '& pre': { 
                                  backgroundColor: '#f5f5f5', 
                                  padding: '1rem', 
                                  borderRadius: '4px',
                                  overflowX: 'auto'
                                },
                                '& code': {
                                  backgroundColor: '#f5f5f5',
                                  padding: '0.2rem 0.4rem',
                                  borderRadius: '3px',
                                  fontSize: '0.9em'
                                },
                                '& p': {
                                  marginBottom: '1rem',
                                  lineHeight: '1.6'
                                },
                                '& ul, & ol': {
                                  marginBottom: '1rem',
                                  paddingLeft: '2rem',
                                  '& li': {
                                    marginBottom: '0.5rem'
                                  }
                                },
                                '& h1, & h2, & h3, & h4, & h5, & h6': {
                                  marginTop: '1.5rem',
                                  marginBottom: '1rem',
                                  fontWeight: 'bold'
                                },
                                '& blockquote': {
                                  borderLeft: '4px solid #e0e0e0',
                                  paddingLeft: '1rem',
                                  marginLeft: 0,
                                  marginBottom: '1rem',
                                  fontStyle: 'italic'
                                },
                                '& table': {
                                  borderCollapse: 'collapse',
                                  width: '100%',
                                  marginBottom: '1rem'
                                },
                                '& th, & td': {
                                  border: '1px solid #e0e0e0',
                                  padding: '0.5rem'
                                },
                                '& th': {
                                  backgroundColor: '#f5f5f5'
                                }
                              }}>
                                <ReactMarkdown components={{
                                  p: ({node, ...props}) => <Typography variant="body1" {...props} />,
                                  h1: ({node, ...props}) => <Typography variant="h1" {...props} />,
                                  h2: ({node, ...props}) => <Typography variant="h2" {...props} />,
                                  h3: ({node, ...props}) => <Typography variant="h3" {...props} />,
                                  h4: ({node, ...props}) => <Typography variant="h4" {...props} />,
                                  h5: ({node, ...props}) => <Typography variant="h5" {...props} />,
                                  h6: ({node, ...props}) => <Typography variant="h6" {...props} />,
                                  li: ({node, ...props}) => <Typography component="li" variant="body1" {...props} />,
                                  blockquote: ({node, ...props}) => <Typography component="blockquote" variant="body1" {...props} />,
                                  code: ({node, inline, ...props}) => (
                                    <Typography
                                      component={inline ? 'span' : 'pre'}
                                      sx={{
                                        backgroundColor: '#f5f5f5',
                                        padding: inline ? '0.2rem 0.4rem' : '1rem',
                                        borderRadius: inline ? '3px' : '4px',
                                        fontSize: inline ? '0.9em' : 'inherit',
                                        overflowX: 'auto',
                                        display: inline ? 'inline' : 'block'
                                      }}
                                      {...props}
                                    />
                                  )
                                }}>
                                  {doc.content}
                                </ReactMarkdown>
                              </Box>
                            </Paper>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default PDFUploader; 