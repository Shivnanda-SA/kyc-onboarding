import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Globe, Package, Shield, ArrowRight } from 'lucide-react';
import { createCase } from '../hooks/useApi';

const COUNTRIES = [
  { code: 'IN', name: 'India' },
  { code: 'SG', name: 'Singapore' },
];

const ENTITY_TYPES = ['company', 'partnership', 'llp', 'trust'];

const PRODUCTS = ['payments', 'cash', 'trade', 'transaction_banking', 'fx'];

const RISK_TIERS = ['low', 'medium', 'high'];

export default function CreateCase() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    jurisdiction: 'IN',
    entity_type: 'company',
    products: [] as string[],
    risk_tier: 'medium',
    client_name: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    if (formData.products.length === 0) {
      setError('Please select at least one product');
      setLoading(false);
      return;
    }
    
    const result = await createCase({
      jurisdiction: formData.jurisdiction,
      entity_type: formData.entity_type,
      products: formData.products,
      risk_tier: formData.risk_tier,
      client_name: formData.client_name || undefined,
    });
    
    if (result) {
      navigate(`/cases/${result.case_id}/upload`);
    } else {
      setError('Failed to create case. Please try again.');
    }
    
    setLoading(false);
  };

  const toggleProduct = (product: string) => {
    setFormData(prev => ({
      ...prev,
      products: prev.products.includes(product)
        ? prev.products.filter(p => p !== product)
        : [...prev.products, product],
    }));
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Building2 className="w-6 h-6 text-primary-700" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Create New Case</h1>
            <p className="text-gray-500">Set up a new client onboarding case</p>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Country Selection */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
              <Globe className="w-4 h-4" />
              Jurisdiction
            </label>
            <div className="grid grid-cols-2 gap-3">
              {COUNTRIES.map(country => (
                <button
                  key={country.code}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, jurisdiction: country.code }))}
                  className={`p-4 rounded-lg border-2 text-left transition-all ${
                    formData.jurisdiction === country.code
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span className="font-semibold text-gray-900">{country.name}</span>
                  <span className="ml-2 text-xs text-gray-500">{country.code}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Entity Type */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
              <Building2 className="w-4 h-4" />
              Entity Type
            </label>
            <select
              value={formData.entity_type}
              onChange={e => setFormData(prev => ({ ...prev, entity_type: e.target.value }))}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              {ENTITY_TYPES.map(type => (
                <option key={type} value={type}>
                  {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          {/* Client Name */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">
              Client Name (optional)
            </label>
            <input
              type="text"
              value={formData.client_name}
              onChange={e => setFormData(prev => ({ ...prev, client_name: e.target.value }))}
              placeholder="Enter client name"
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* Products */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
              <Package className="w-4 h-4" />
              Products
            </label>
            <div className="flex flex-wrap gap-2">
              {PRODUCTS.map(product => (
                <button
                  key={product}
                  type="button"
                  onClick={() => toggleProduct(product)}
                  className={`px-4 py-2 rounded-full text-sm transition-all ${
                    formData.products.includes(product)
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {product.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Risk Tier */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
              <Shield className="w-4 h-4" />
              Risk Tier
            </label>
            <div className="flex gap-3">
              {RISK_TIERS.map(tier => (
                <button
                  key={tier}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, risk_tier: tier }))}
                  className={`flex-1 p-3 rounded-lg border-2 capitalize transition-all ${
                    formData.risk_tier === tier
                      ? tier === 'high'
                        ? 'border-red-500 bg-red-50 text-red-700'
                        : tier === 'medium'
                        ? 'border-yellow-500 bg-yellow-50 text-yellow-700'
                        : 'border-green-500 bg-green-50 text-green-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {tier}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-primary-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Creating...
              </>
            ) : (
              <>
                Continue to Upload
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
