import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload } from 'lucide-react';

const UploadSection = ({ onUpload, type, isLoading }) => {
    const onDrop = useCallback(acceptedFiles => {
        if (acceptedFiles?.length > 0) {
            onUpload(acceptedFiles[0]);
        }
    }, [onUpload]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: type === 'image'
            ? { 'image/*': ['.jpeg', '.jpg', '.png'] }
            : { 'video/*': ['.mp4', '.mov', '.avi'] },
        multiple: false,
        disabled: isLoading
    });

    return (
        <div {...getRootProps()} className={`upload-zone ${isDragActive ? 'active' : ''}`}>
            <input {...getInputProps()} />
            <div className="upload-icon">
                <Upload size={80} strokeWidth={1.5} />
            </div>
            {isLoading ? (
                <div className="upload-text">Processing...</div>
            ) : (
                <>
                    <h3 className="upload-text">
                        {isDragActive ? `Drop the ${type} here` : `Drag & drop ${type} here`}
                    </h3>
                    <p className="upload-subtext">or click to select file</p>
                </>
            )}
        </div>
    );
};

export default UploadSection;
