import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './components/Home';
import Login from './components/Login';
import Chatbot from './components/Chatbot';
import TableAgentPage from './components/TableAgent';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/chatbot" element={<Chatbot />} />
          <Route path="/table-agent" element={<TableAgentPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
