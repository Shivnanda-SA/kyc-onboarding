import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Upload, File, X, ArrowRight } from 'lucide-react';
import { uploadDocuments, processCase } from '../hooks/useApi';

const ALLOWED_TYPES = ['.pdf', '.docx', '.png', '.jpg', '.jpeg', '.txt'];

export default function UploadDocuments() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processProgress, setProcessProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!processing) {
      setProcessProgress(0);
      return;
    }

    // Simulated progress (no backend progress events yet): ramp to 90% smoothly.
    setProcessProgress(5);
    const start = Date.now();
    const id = window.setInterval(() => {
      const elapsed = Date.now() - start;
      // Ease-out curve up to 90% over ~25s.
      const t = Math.min(1, elapsed / 25000);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = Math.min(90, Math.max(5, Math.round(5 + eased * 85)));
      setProcessProgress(prev => (prev >= 90 ? prev : Math.max(prev, next)));
    }, 250);

    return () => window.clearInterval(id);
  }, [processing]);

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const handleUpload = async () => {
    if (!caseId || files.length === 0) return;
    
    setUploading(true);
    setError(null);
    
    const result = await uploadDocuments(caseId, files);
    
    if (result) {
      setFiles([]);
      setProcessing(true);
      setProcessProgress(10);
      
      const processResult = await processCase(caseId);
      
      if (processResult) {
        setProcessProgress(100);
        navigate(`/cases/${caseId}/results`);
      } else {
        setError('Documents uploaded but processing failed. Please try again.');
        setProcessing(false);
      }
    } else {
      setError('Upload failed. Please try again.');
    }
    
    setUploading(false);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Upload className="w-6 h-6 text-primary-700" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Upload Documents</h1>
            <p className="text-gray-500">Upload KYC documents for processing</p>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {processing && (
          <div className="mb-6">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-gray-700 font-medium">Processing documents…</span>
              <span className="font-medium text-gray-900">{processProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-primary-600 h-2 rounded-full transition-all"
                style={{ width: `${processProgress}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Extracting text, classifying documents, and evaluating checklist.
            </p>
          </div>
        )}

        {/* Drop Zone */}
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-primary-400 transition-colors"
        >
          <div className="w-16 h-16 bg-primary-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <Upload className="w-8 h-8 text-primary-600" />
          </div>
          <p className="text-lg font-medium text-gray-900 mb-2">
            Drag and drop your documents
          </p>
          <p className="text-gray-500 mb-4">
            or click to browse files
          </p>
          <p className="text-xs text-gray-400 mb-4">
            Supported: PDF, DOCX, PNG, JPG, TXT (max 25MB each)
          </p>
          <input
            type="file"
            multiple
            accept={ALLOWED_TYPES.join(',')}
            onChange={handleFileInput}
            className="hidden"
            id="file-input"
          />
          <label
            htmlFor="file-input"
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 cursor-pointer transition-colors"
          >
            Browse Files
          </label>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Selected Files ({files.length})
            </h3>
            <div className="space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg">
                      <File className="w-5 h-5 text-gray-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 truncate max-w-xs">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(file.size)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                  >
                    <X className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 mt-8">
          <button
            onClick={() => navigate(`/cases/${caseId}/results`)}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Skip Upload
          </button>
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || uploading || processing}
            className="flex-1 flex items-center justify-center gap-2 bg-primary-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {processing ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Processing...
              </>
            ) : uploading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                Upload & Process
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
