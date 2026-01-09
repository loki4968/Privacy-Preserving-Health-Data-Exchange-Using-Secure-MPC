'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '../../../context/AuthContext';
import ComputationResults from '../../../components/ComputationResults';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function ComputationResultsPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const computationId = params.id;

  if (!user) {
    router.push('/login');
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <Link
            href={`/secure-computations/${computationId}`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Computation Details
          </Link>
          
          <div className="bg-white rounded-lg shadow-md p-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Computation Results
            </h1>
            <p className="text-gray-600">
              Detailed results for computation {computationId.substring(0, 16)}...
            </p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <ComputationResults computationId={computationId} />
        </div>
      </div>
    </div>
  );
}

